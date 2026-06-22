from __future__ import annotations

import asyncio
import logging
import re
import time
import traceback
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable

from locust.exception import CatchResponseError, RescheduleTask
from locust_plugins.users.playwright import PlaywrightScriptUser, PlaywrightUser, sync


class NetworkByteCollector:
    def __init__(self, page) -> None:
        self.page = page
        self._active_windows: dict[int, int] = {}
        self._next_window_id = 0
        self._pending_tasks: set[asyncio.Task[int | None]] = set()
        self._attached = False

    def attach(self) -> None:
        if self._attached:
            return
        self.page.on("response", self._handle_response)
        self._attached = True

    def start_window(self) -> int:
        window_id = self._next_window_id
        self._next_window_id += 1
        self._active_windows[window_id] = 0
        return window_id

    def finish_window(self, window_id: int) -> int:
        return self._active_windows.pop(window_id, 0)

    async def settle(self) -> None:
        while self._pending_tasks:
            pending = tuple(self._pending_tasks)
            await asyncio.gather(*pending, return_exceptions=True)

    async def checkpoint(self) -> None:
        await self.settle()

    def _handle_response(self, response) -> None:
        task = asyncio.create_task(self._consume_response(response))
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    async def _consume_response(self, response) -> int | None:
        try:
            body = await response.body()
        except Exception:
            return None

        size = len(body)
        for window_id in tuple(self._active_windows):
            self._active_windows[window_id] += size
        return size


def ensure_byte_collector(user: PlaywrightUser) -> NetworkByteCollector:
    collector = getattr(user, "_network_byte_collector", None)
    if collector is None:
        collector = NetworkByteCollector(user.page)
        collector.attach()
        setattr(user, "_network_byte_collector", collector)
    return collector


def _format_error(exc: Exception, *, include_url: str = "") -> Exception:
    try:
        message = exc.message + include_url  # type: ignore[attr-defined]
        return CatchResponseError(re.sub("=======*", "", message).replace("\n", "").replace(" logs ", " ")[:500])
    except Exception:
        return exc


async def _capture_error_screenshot(user: PlaywrightUser, *, full_page: bool) -> None:
    if user.error_screenshot_made:
        return
    user.error_screenshot_made = True
    if user.page:
        await user.page.screenshot(
            path="screenshot_" + time.strftime("%Y%m%d_%H%M%S") + ".png",
            full_page=full_page,
        )


def _fire_request_event(
    user: PlaywrightUser,
    *,
    request_type: str,
    name: str,
    start_time: float,
    start_perf_counter: float,
    response_length: int,
    exception: Exception | None,
) -> None:
    user.environment.events.request.fire(
        request_type=request_type,
        name=name,
        start_time=start_time,
        response_time=(time.perf_counter() - start_perf_counter) * 1000,
        response_length=response_length,
        context={**user.context()},
        url=user.page.url if user.page else None,
        exception=exception,
    )


@asynccontextmanager
async def event(
    user: PlaywrightUser,
    name: str = "unnamed",
    request_type: str = "event",
):
    collector = ensure_byte_collector(user)
    window_id = collector.start_window()
    start_time = time.time()
    start_perf_counter = time.perf_counter()
    try:
        yield
        await collector.checkpoint()
        _fire_request_event(
            user,
            request_type=request_type,
            name=name,
            start_time=start_time,
            start_perf_counter=start_perf_counter,
            response_length=collector.finish_window(window_id),
            exception=None,
        )
    except Exception as exc:
        error = _format_error(exc)
        await _capture_error_screenshot(user, full_page=False)
        await collector.checkpoint()
        _fire_request_event(
            user,
            request_type=request_type,
            name=name,
            start_time=start_time,
            start_perf_counter=start_perf_counter,
            response_length=collector.finish_window(window_id),
            exception=error,
        )
        raise
    finally:
        await asyncio.sleep(0.1)


async def run_task(user: PlaywrightUser, func: Callable[[PlaywrightUser, Any], Awaitable[None]]) -> None:
    if user.browser_context:
        await user.browser_context.close()
    user.browser_context = await user.browser.new_context(ignore_https_errors=True, base_url=user.host)
    user.page = await user.browser_context.new_page()
    user.page.set_default_timeout(60000)

    collector = NetworkByteCollector(user.page)
    collector.attach()
    setattr(user, "_network_byte_collector", collector)

    if isinstance(user, PlaywrightScriptUser):
        name = user.script
    else:
        name = user.__class__.__name__ + "." + func.__name__

    task_window_id = collector.start_window()
    task_start_time = time.time()
    start_perf_counter = time.perf_counter()

    try:
        await func(user, user.page)
        if user.log_tasks:
            await collector.checkpoint()
            _fire_request_event(
                user,
                request_type="TASK",
                name=name,
                start_time=task_start_time,
                start_perf_counter=start_perf_counter,
                response_length=collector.finish_window(task_window_id),
                exception=None,
            )
    except RescheduleTask:
        collector.finish_window(task_window_id)
    except Exception as exc:
        error = _format_error(exc, include_url=user.page.url if user.page else "")
        await _capture_error_screenshot(user, full_page=True)
        if user.log_tasks:
            await collector.checkpoint()
            _fire_request_event(
                user,
                request_type="TASK",
                name=name,
                start_time=task_start_time,
                start_perf_counter=start_perf_counter,
                response_length=collector.finish_window(task_window_id),
                exception=error,
            )
        else:
            collector.finish_window(task_window_id)
            user.environment.events.user_error.fire(
                user_instance=user,
                exception=error,
                tb=error.__traceback__,
            )
            logging.error("%s\n%s", error, traceback.format_exc())
    finally:
        try:
            if user.page:
                await user.page.wait_for_timeout(1000)
            await collector.settle()
        finally:
            setattr(user, "_network_byte_collector", None)
            if user.page:
                await user.page.close()
            if user.browser_context:
                await user.browser_context.close()


def pw(func: Callable[[PlaywrightUser, Any], Awaitable[None]]):
    @sync
    async def wrapped(user: PlaywrightUser):
        await run_task(user, func)

    return wrapped

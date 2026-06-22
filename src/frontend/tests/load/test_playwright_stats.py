from __future__ import annotations

import asyncio
from types import SimpleNamespace

from tests.load.load_support.playwright_stats import NetworkByteCollector, ensure_byte_collector, event, run_task


class FakeResponse:
    def __init__(self, payload: bytes = b"", exc: Exception | None = None, delay_seconds: float = 0) -> None:
        self.payload = payload
        self.exc = exc
        self.delay_seconds = delay_seconds

    async def body(self) -> bytes:
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        if self.exc is not None:
            raise self.exc
        return self.payload


class FakePage:
    def __init__(self) -> None:
        self.listeners: dict[str, object] = {}
        self.screenshots: list[dict[str, object]] = []
        self.timeout_ms: int | None = None
        self.waited_ms: int | None = None
        self.closed = False
        self.url = "http://example.test/page"

    def on(self, event_name: str, callback) -> None:
        self.listeners[event_name] = callback

    def emit_response(self, response: FakeResponse) -> None:
        callback = self.listeners["response"]
        callback(response)

    def set_default_timeout(self, timeout_ms: int) -> None:
        self.timeout_ms = timeout_ms

    async def screenshot(self, *, path: str, full_page: bool) -> None:
        self.screenshots.append({"path": path, "full_page": full_page})

    async def wait_for_timeout(self, timeout_ms: int) -> None:
        self.waited_ms = timeout_ms

    async def close(self) -> None:
        self.closed = True


class FakeBrowserContext:
    def __init__(self, page: FakePage) -> None:
        self.page = page
        self.closed = False

    async def new_page(self) -> FakePage:
        return self.page

    async def close(self) -> None:
        self.closed = True


class FakeBrowser:
    def __init__(self, page: FakePage) -> None:
        self.page = page
        self.contexts: list[FakeBrowserContext] = []

    async def new_context(self, **_kwargs) -> FakeBrowserContext:
        context = FakeBrowserContext(self.page)
        self.contexts.append(context)
        return context


class FakeSink:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def fire(self, **kwargs) -> None:
        self.calls.append(kwargs)


class FakeUser:
    def __init__(self, page: FakePage | None = None) -> None:
        self.environment = SimpleNamespace(
            events=SimpleNamespace(
                request=FakeSink(),
                user_error=FakeSink(),
            )
        )
        self.page = page
        self.browser = FakeBrowser(page or FakePage())
        self.browser_context = None
        self.host = "http://ingress:8080"
        self.error_screenshot_made = False
        self.log_tasks = True

    def context(self) -> dict[str, object]:
        return {}


def test_network_byte_collector_counts_multiple_responses() -> None:
    async def scenario() -> None:
        page = FakePage()
        collector = NetworkByteCollector(page)
        collector.attach()

        window_id = collector.start_window()
        page.emit_response(FakeResponse(b"abc"))
        page.emit_response(FakeResponse(b"defgh"))
        await collector.settle()

        assert collector.finish_window(window_id) == 8

    asyncio.run(scenario())


def test_network_byte_collector_isolates_windows() -> None:
    async def scenario() -> None:
        page = FakePage()
        collector = NetworkByteCollector(page)
        collector.attach()

        first_window = collector.start_window()
        page.emit_response(FakeResponse(b"abc"))
        await collector.settle()
        assert collector.finish_window(first_window) == 3

        second_window = collector.start_window()
        page.emit_response(FakeResponse(b"hello"))
        await collector.settle()
        assert collector.finish_window(second_window) == 5

    asyncio.run(scenario())


def test_network_byte_collector_checkpoint_drains_pending_responses() -> None:
    async def scenario() -> None:
        page = FakePage()
        collector = NetworkByteCollector(page)
        collector.attach()

        window_id = collector.start_window()
        page.emit_response(FakeResponse(b"delayed", delay_seconds=0.01))
        await collector.checkpoint()

        assert collector.finish_window(window_id) == 7

    asyncio.run(scenario())


def test_page_event_records_partial_bytes_on_failure() -> None:
    async def scenario() -> None:
        page = FakePage()
        user = FakeUser(page)
        collector = ensure_byte_collector(user)

        try:
            async with event(user, "assess:list_ready", "PAGE"):
                page.emit_response(FakeResponse(b"partial"))
                await collector.settle()
                raise RuntimeError("boom")
        except RuntimeError as exc:
            assert str(exc) == "boom"
        else:
            raise AssertionError("event should re-raise flow failures")

        request_call = user.environment.events.request.calls[0]
        assert request_call["name"] == "assess:list_ready"
        assert request_call["request_type"] == "PAGE"
        assert request_call["response_length"] == 7
        assert isinstance(request_call["exception"], RuntimeError)
        assert page.screenshots[0]["full_page"] is False

    asyncio.run(scenario())


def test_task_and_page_windows_record_separate_byte_totals() -> None:
    async def scenario() -> None:
        page = FakePage()
        user = FakeUser(page)

        async def measured_task(task_user, task_page: FakePage) -> None:
            collector = ensure_byte_collector(task_user)
            async with event(task_user, "assess:list_ready", "PAGE"):
                task_page.emit_response(FakeResponse(b"hello world"))
                await collector.settle()
            task_page.emit_response(FakeResponse(b"goodbye"))
            await collector.settle()

        await run_task(user, measured_task)

        page_call, task_call = user.environment.events.request.calls
        assert page_call["request_type"] == "PAGE"
        assert page_call["response_length"] == 11
        assert task_call["request_type"] == "TASK"
        assert task_call["response_length"] == 18
        assert page.waited_ms == 1000
        assert page.closed is True
        assert user.browser.contexts[0].closed is True

    asyncio.run(scenario())


def test_failed_page_event_records_failed_task() -> None:
    async def scenario() -> None:
        page = FakePage()
        user = FakeUser(page)

        async def measured_task(task_user, task_page: FakePage) -> None:
            collector = ensure_byte_collector(task_user)
            async with event(task_user, "assess:list_ready", "PAGE"):
                task_page.emit_response(FakeResponse(b"partial"))
                await collector.settle()
                raise RuntimeError("boom")

        await run_task(user, measured_task)

        page_call, task_call = user.environment.events.request.calls
        assert page_call["request_type"] == "PAGE"
        assert page_call["response_length"] == 7
        assert isinstance(page_call["exception"], RuntimeError)
        assert task_call["request_type"] == "TASK"
        assert task_call["name"] == "FakeUser.measured_task"
        assert task_call["response_length"] == 7
        assert isinstance(task_call["exception"], RuntimeError)

    asyncio.run(scenario())

from collections.abc import Callable, Iterator
from concurrent.futures import Future
from contextlib import contextmanager, suppress
from threading import Thread, Timer
from time import monotonic

import requests


@contextmanager
def response_with_deadline(send: Callable[[], requests.Response], deadline: float) -> Iterator[requests.Response]:
    def remaining_time() -> float:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError("HTTP response deadline exceeded")
        return remaining

    pending: Future[requests.Response] = Future()

    def send_request() -> None:
        try:
            pending.set_result(send())
        except Exception as exc:
            pending.set_exception(exc)

    def close_late_response(result: Future[requests.Response]) -> None:
        with suppress(Exception):
            result.result().close()

    remaining = remaining_time()
    Thread(target=send_request, daemon=True).start()
    try:
        try:
            response = pending.result(timeout=remaining)
        except TimeoutError:
            pending.add_done_callback(close_late_response)
            raise
        with response:
            # Interrupt a blocked streaming read even if the peer keeps sending data.
            def stop_reading() -> None:
                with suppress(AttributeError, OSError, RuntimeError, ValueError):
                    response.raw.shutdown()

            timer = Timer(remaining_time(), stop_reading)
            timer.daemon = True
            timer.start()
            try:
                yield response
            finally:
                timer.cancel()
                timer.join()
    finally:
        remaining_time()

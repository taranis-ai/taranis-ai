"""HTTP connections owned by one task, with separate service and source policies."""

from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from typing import Any

import niquests

from worker.config import Config


_sessions: ContextVar[dict[bool, niquests.Session] | None] = ContextVar("http_sessions", default=None)


@contextmanager
def http_session_scope() -> Iterator[None]:
    """Reuse connections in nested calls and close them when the outer task exits."""
    if _sessions.get() is not None:
        yield
        return

    sessions: dict[bool, niquests.Session] = {}
    token = _sessions.set(sessions)
    try:
        yield
    finally:
        _sessions.reset(token)
        with ExitStack() as cleanup:
            for session in sessions.values():
                cleanup.callback(session.close)


def http_request(method: str, url: str, *, external: bool = False, timeout: int = 60, **kwargs: Any) -> niquests.Response:
    """Fetch a buffered response; calls outside tasks own a temporary session.

    Credentials and proxies remain request-local. External requests keep cookies
    within a redirect chain, but never carry them into the next fetch.
    """
    with http_session_scope():
        sessions = _sessions.get()
        assert sessions is not None
        if external not in sessions:
            sessions[external] = niquests.Session(
                retries=0,
                disable_http3=Config.DISABLE_HTTP3 if external else True,
                allow_incoming_cookies=external,
            )
        session = sessions[external]
        try:
            response = session.request(
                method,
                url,
                timeout=(min(10 if external else 5, timeout), timeout),
                allow_redirects=external,
                **kwargs,
            )
            if not external and response.status_code is not None and 300 <= response.status_code < 400:
                raise niquests.HTTPError("Unexpected redirect from service endpoint", response=response)
            return response
        finally:
            session.cookies.clear()

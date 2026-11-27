"""HTTP connections owned by one task, with separate service and source policies."""

import errno
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from typing import Any

import niquests

from worker.config import Config
from worker.log import logger


_sessions: ContextVar[dict[str, niquests.Session] | None] = ContextVar("http_sessions", default=None)


@contextmanager
def http_session_scope() -> Iterator[None]:
    """Reuse connections in nested calls and close them when the outer task exits."""
    if _sessions.get() is not None:
        yield
        return

    sessions: dict[str, niquests.Session] = {}
    token = _sessions.set(sessions)
    try:
        yield
    finally:
        _sessions.reset(token)
        with ExitStack() as cleanup:
            for session in sessions.values():
                cleanup.callback(session.close)


def _is_message_too_long(error: BaseException | None) -> bool:
    while error is not None:
        if isinstance(error, OSError) and error.errno == errno.EMSGSIZE:
            return True
        error = error.__cause__ or error.__context__
    return False


def http_request(method: str, url: str, *, external: bool = False, timeout: int = 60, **kwargs: Any) -> niquests.Response:
    """Fetch a buffered response; calls outside tasks own a temporary session.

    Credentials and proxies remain request-local. External requests keep cookies
    within a redirect chain, but never carry them into the next fetch.
    """
    with http_session_scope():
        sessions = _sessions.get()
        assert sessions is not None

        def send(pool: str) -> niquests.Response:
            if pool not in sessions:
                sessions[pool] = niquests.Session(retries=0, disable_http3=pool != "external", allow_incoming_cookies=external)
            session = sessions[pool]
            try:
                return session.request(
                    method, url, timeout=(min(10 if external else 5, timeout), timeout), allow_redirects=external, **kwargs
                )
            finally:
                session.cookies.clear()

        if external:
            if Config.DISABLE_HTTP3 or "external_tcp" in sessions:
                return send("external_tcp")
            try:
                return send("external")
            except (niquests.ConnectionError, niquests.exceptions.ChunkedEncodingError) as exc:
                if method.upper() != "GET" or not _is_message_too_long(exc):
                    raise
            logger.info("External GET hit EMSGSIZE with HTTP/3 enabled. Retrying over TCP for this task.")
            return send("external_tcp")

        response = send("service")
        if response.status_code is not None and 300 <= response.status_code < 400:
            raise niquests.HTTPError("Unexpected redirect from service endpoint", response=response)
        return response

from unittest.mock import Mock

import pytest
import responses

from frontend.config import Config
from frontend.core_api import CoreApi


def test_core_clients_isolate_tokens_and_close_at_request_end(app, monkeypatch):
    monkeypatch.setattr(Config, "TARANIS_CORE_URL", "http://core.example")
    with responses.RequestsMock() as upstream:
        upstream.get("http://core.example/echo", json={"ok": True})
        with app.test_request_context(headers={"Cookie": f"{Config.JWT_ACCESS_COOKIE_NAME}=browser-token"}):
            first = CoreApi()
            assert first.api_get("/echo") == {"ok": True}
            second = CoreApi()
            assert second.api_get("/echo") == {"ok": True}
            assert second.session is first.session

            explicit = CoreApi(jwt_token="explicit-token")
            explicit.api_get("/echo")
            assert explicit.session is not first.session
            assert [call.request.headers["Authorization"] for call in upstream.calls] == [
                "Bearer browser-token",
                "Bearer browser-token",
                "Bearer explicit-token",
            ]
            close_first = Mock(wraps=first.session.close)
            close_explicit = Mock(wraps=explicit.session.close)
            monkeypatch.setattr(first.session, "close", close_first)
            monkeypatch.setattr(explicit.session, "close", close_explicit)

        close_first.assert_called_once()
        close_explicit.assert_called_once()
        with app.test_request_context():
            assert CoreApi(jwt_token="browser-token").session is not first.session


@pytest.mark.parametrize("consume", ["complete", "partial", "none", "discard"])
def test_download_stream_closes_upstream_and_session(app, monkeypatch, consume):
    monkeypatch.setattr(Config, "TARANIS_CORE_URL", "http://core.example")
    with responses.RequestsMock() as upstream:
        payload = b"export data" * 10000
        upstream.get("http://core.example/download", body=payload, content_type="application/octet-stream")
        with app.test_request_context():
            api = CoreApi()
            download_session = api._new_session()
            close_download_session = Mock(wraps=download_session.close)
            monkeypatch.setattr(download_session, "close", close_download_session)
            monkeypatch.setattr(api, "_new_session", lambda: download_session)
            downloaded = api.api_download("/download")
            close_session = Mock(wraps=api.session.close)
            monkeypatch.setattr(api.session, "close", close_session)
            if consume != "discard":
                proxied = api.stream_proxy(downloaded, "export.bin")
        close_session.assert_called_once()
        if consume != "discard":
            close_download_session.assert_not_called()
            if consume == "complete":
                assert b"".join(proxied.response) == payload
            elif consume == "partial":
                assert next(iter(proxied.response)) == payload[: 64 * 1024]
            proxied.close()
        assert downloaded.raw.closed
        close_download_session.assert_called_once()

from contextlib import nullcontext

import niquests
import pytest

from worker.bot_api import BotApi
from worker.collectors.base_web_collector import BaseWebCollector
from worker.config import Config
from worker.core_api import CoreApi
from worker.http_client import http_request, http_session_scope


@pytest.mark.parametrize("fail", [False, True])
def test_task_reuses_connections_and_closes_them_on_exit(http_server, monkeypatch, fail):
    monkeypatch.setattr(Config, "TARANIS_CORE_URL", http_server.url)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    ports = set()
    with pytest.raises(RuntimeError, match="task failed") if fail else nullcontext(), http_session_scope():
        first = CoreApi().api_get("/echo")
        second = CoreApi().api_get("/echo")
        assert first["port"] == second["port"]
        assert second["cookie"] is None
        ports.add(first["port"])

        with http_session_scope():
            collector = BaseWebCollector()
            article = collector.send_get_request(f"{http_server.url}/redirect").json()
            icon = collector._fetch_icon(f"{http_server.url}/echo").json()
            assert article["port"] == icon["port"]
            assert article["cookie"] == "upstream=secret"
            assert icon["cookie"] is None
            assert article["authorization"] is None
            ports.add(article["port"])

        assert len(ports) == 2
        assert CoreApi().api_get("/echo")["port"] == first["port"]
        if fail:
            raise RuntimeError("task failed")

    assert {http_server.closed_connections.get(timeout=2) for _ in ports} == ports
    with http_session_scope():
        later = CoreApi().api_get("/echo")
        assert later["port"] not in ports
    assert http_server.closed_connections.get(timeout=2) == later["port"]


def test_service_redirects_and_failures_are_not_replayed(http_server, monkeypatch):
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    with http_session_scope():
        with pytest.raises(niquests.HTTPError, match="Unexpected redirect"):
            http_request("POST", f"{http_server.url}/redirect", json={"publish": True})
        assert http_request("POST", f"{http_server.url}/unavailable").status_code == 503
    assert http_server.received == [("POST", "/redirect"), ("POST", "/unavailable")]


def test_standalone_bot_calls_close_connections_and_use_updated_credentials(http_server, monkeypatch):
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    bot = BotApi(http_server.url, bot_api_key="first")
    first = bot.api_get("/echo")
    assert first["authorization"] == "Bearer first"
    assert http_server.closed_connections.get(timeout=2) == first["port"]

    bot.update_parameters(http_server.url, "second")
    second = bot.api_get("/echo")
    assert second["authorization"] == "Bearer second"
    assert second["cookie"] is None
    assert http_server.closed_connections.get(timeout=2) == second["port"]

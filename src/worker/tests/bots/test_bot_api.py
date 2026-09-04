import logging

import pytest
from niquests.exceptions import RequestException

from worker.bot_api import BotApi, BotServiceUnavailableError
from worker.config import Config


@pytest.mark.parametrize("timeout_input, expected_value", [(42, 42), (None, Config.REQUESTS_TIMEOUT)])
def test_bot_api_timeout_resolve(timeout_input, expected_value):
    bot_api = BotApi("http://example.invalid", requests_timeout=timeout_input)
    assert bot_api.timeout == expected_value


@pytest.mark.parametrize("request_method", ["get", "post"])
def test_bot_api_reports_transport_failure(request_method, monkeypatch, caplog):
    def raise_request_error(**_):
        raise RequestException("connection refused")

    monkeypatch.setattr(f"worker.bot_api.requests.{request_method}", raise_request_error)
    caplog.set_level(logging.ERROR)

    with pytest.raises(BotServiceUnavailableError) as exc_info:
        getattr(BotApi("http://bot.example"), f"api_{request_method}")("/analyze")

    assert exc_info.value.__cause__ is None
    assert f"Bot service {request_method.upper()} request to http://bot.example/analyze failed: connection refused" in caplog.text

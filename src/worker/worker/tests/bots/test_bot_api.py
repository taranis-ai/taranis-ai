from worker.bot_api import BotApi
from worker.config import Config


def test_bot_api_timeout_uses_parameter_override():
    bot_api = BotApi("http://example.invalid", requests_timeout="42")
    assert bot_api.timeout == 42


def test_bot_api_timeout_falls_back_when_parameter_missing():
    bot_api = BotApi("http://example.invalid", requests_timeout="")
    assert bot_api.timeout == Config.REQUESTS_TIMEOUT


def test_bot_api_timeout_falls_back_when_parameter_invalid():
    bot_api = BotApi("http://example.invalid", requests_timeout="not-a-number")
    assert bot_api.timeout == Config.REQUESTS_TIMEOUT

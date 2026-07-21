import pytest

from worker.bot_api import BotApi
from worker.config import Config


@pytest.mark.parametrize(
    "timeout_input, expected_value",
    [
        ("42", 42),
        ("", Config.REQUESTS_TIMEOUT),
        ("character", Config.REQUESTS_TIMEOUT),
        (-1, Config.REQUESTS_TIMEOUT),
        (0, Config.REQUESTS_TIMEOUT),
        (None, Config.REQUESTS_TIMEOUT),
    ],
)
def test_bot_api_timeout_resolve(timeout_input, expected_value):
    bot_api = BotApi("http://example.invalid", requests_timeout=timeout_input)
    assert bot_api.timeout == expected_value

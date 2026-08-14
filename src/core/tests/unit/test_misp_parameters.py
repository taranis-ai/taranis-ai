import pytest

from core.config import Config
from core.model.connector import Connector
from core.model.osint_source import OSINTSource
from core.model.parameter_value import ParameterValue
from core.model.settings import Settings


@pytest.mark.parametrize("value", ["", "1", "60"])
def test_positive_int_accepts_empty_optional_and_positive_values(value):
    assert ParameterValue("REQUEST_TIMEOUT", value, rules="positive_int").check_rules()


@pytest.mark.parametrize("value", ["0", "-1", "1.5", "invalid"])
def test_positive_int_rejects_non_positive_and_non_integer_values(value):
    with pytest.raises(ValueError, match="positive integer"):
        ParameterValue("REQUEST_TIMEOUT", value, rules="positive_int").check_rules()


@pytest.mark.parametrize(
    "normalize,worker_type",
    [
        (OSINTSource.get_with_defaults, "misp_collector"),
        (Connector.get_with_defaults, "misp_connector"),
    ],
)
def test_misp_worker_parameters_apply_defaults_and_global_proxy(monkeypatch, normalize, worker_type):
    monkeypatch.setattr(
        Settings,
        "get_settings",
        classmethod(lambda cls: {"default_collector_proxy": "http://global-proxy:8080"}),
    )
    data = {
        "type": worker_type,
        "parameters": {
            "SSL_CHECK": "",
            "REQUEST_TIMEOUT": "",
            "PROXY_SERVER": "http://local-proxy:8080",
            "USE_GLOBAL_PROXY": "true",
        },
    }

    parameters = normalize(data)["parameters"]

    assert parameters["SSL_CHECK"] == "false"
    assert parameters["REQUEST_TIMEOUT"] == str(Config.REQUESTS_TIMEOUT)
    assert parameters["PROXY_SERVER"] == "http://global-proxy:8080"

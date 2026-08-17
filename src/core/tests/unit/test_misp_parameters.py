import pytest

from core.config import Config
from core.managers.pre_seed_data import workers
from core.model.connector import Connector
from core.model.osint_source import OSINTSource
from core.model.parameter_value import ParameterValue
from core.model.settings import Settings


@pytest.mark.parametrize("value", ["", "1", "60"])
def test_positive_int_accepts_empty_optional_and_positive_values(value):
    ParameterValue("REQUEST_TIMEOUT", rules="positive_int").check_value_rules(value)


@pytest.mark.parametrize("value", ["0", "-1", "1.5", "invalid"])
def test_positive_int_rejects_non_positive_and_non_integer_values(value):
    with pytest.raises(ValueError, match="positive integer"):
        ParameterValue("REQUEST_TIMEOUT", rules="positive_int").check_value_rules(value)


@pytest.mark.parametrize("worker_type", ["MISP_COLLECTOR", "MISP_CONNECTOR"])
def test_misp_request_timeout_preseed_uses_positive_int(worker_type):
    worker = next(worker for worker in workers if worker["type"] == worker_type)
    request_timeout = next(parameter for parameter in worker["parameters"] if parameter["parameter"] == "REQUEST_TIMEOUT")

    assert request_timeout["rules"] == "positive_int"


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


@pytest.mark.parametrize(
    "normalize,worker_type",
    [
        (OSINTSource.get_with_defaults, "misp_collector"),
        (Connector.get_with_defaults, "misp_connector"),
    ],
)
def test_misp_worker_parameters_skip_settings_without_global_proxy(monkeypatch, normalize, worker_type):
    def unexpected_settings_query(cls):
        raise AssertionError("Settings should not be queried")

    monkeypatch.setattr(Settings, "get_settings", classmethod(unexpected_settings_query))
    data = {
        "type": worker_type,
        "parameters": {
            "REQUEST_TIMEOUT": "30",
            "PROXY_SERVER": "http://local-proxy:8080",
            "USE_GLOBAL_PROXY": "false",
        },
    }

    parameters = normalize(data)["parameters"]

    assert parameters["PROXY_SERVER"] == "http://local-proxy:8080"

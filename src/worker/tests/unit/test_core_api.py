from worker import core_api
from worker.config import Config, Settings
from worker.core_api import CoreApi


def test_otlp_endpoint_is_normalized():
    settings = Settings(OTEL_EXPORTER_OTLP_ENDPOINT="  http://telemetry:4318/  ")

    assert settings.OTEL_EXPORTER_OTLP_ENDPOINT == "http://telemetry:4318"


def test_core_api_injects_current_trace_context(monkeypatch):
    monkeypatch.setattr(core_api, "inject", lambda carrier: carrier.update({"traceparent": "test-trace"}))

    api = CoreApi()

    assert "traceparent" not in api.headers
    assert api.get_request_headers()["traceparent"] == "test-trace"


def test_update_osint_source_icon_skips_empty_file(requests_mock):
    assert CoreApi().update_osint_source_icon("source-1", {"file": ("favicon.ico", b"")}) is None

    assert requests_mock.request_history == []


def test_update_osint_source_icon_sends_multipart_file(requests_mock):
    requests_mock.put(f"{Config.TARANIS_CORE_URL}/worker/osint-sources/source-1/icon", json={"message": "Icon uploaded"})

    result = CoreApi().update_osint_source_icon("source-1", {"file": ("favicon.ico", b"icon")})

    assert result == {"message": "Icon uploaded"}
    assert requests_mock.request_history[0].headers["Content-Type"].startswith("multipart/form-data")


def test_run_post_collection_bots_forwards_current_job_user(requests_mock, monkeypatch):
    requests_mock.put(f"{Config.TARANIS_CORE_URL}/worker/post-collection-bots", json={"message": "scheduled"})
    monkeypatch.setattr(CoreApi, "_get_current_job_user_id", staticmethod(lambda: "user-1"))

    result = CoreApi().run_post_collection_bots("source-1")

    assert result == {"message": "scheduled"}
    assert requests_mock.request_history[0].json() == {"source_id": "source-1", "user_id": "user-1"}

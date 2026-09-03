from unittest.mock import patch

from flask import Flask
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from frontend import setup
from frontend.config import Config


def test_setup_telemetry_instruments_flask_requests(monkeypatch):
    endpoint = "http://collector:4318"
    service_name = "custom-frontend"
    monkeypatch.setattr(Config, "OTEL_EXPORTER_OTLP_ENDPOINT", endpoint)
    monkeypatch.setattr(Config, "OTEL_SERVICE_NAME", service_name)
    exporter = InMemorySpanExporter()
    metric_reader = InMemoryMetricReader()
    app = Flask(__name__)
    app.get("/test")(lambda: "ok")

    with (
        patch.object(setup, "OTLPSpanExporter", return_value=exporter) as exporter_factory,
        patch.object(setup, "OTLPMetricExporter") as metric_exporter_factory,
        patch.object(setup, "BatchSpanProcessor", SimpleSpanProcessor),
        patch.object(setup, "PeriodicExportingMetricReader", return_value=metric_reader),
        patch.object(setup, "RequestsInstrumentor") as requests_instrumentor,
    ):
        setup.setup_telemetry(app)
        response = app.test_client().get("/test")

    spans = exporter.get_finished_spans()
    assert response.status_code == 200
    assert len(spans) == 1
    span = spans[0]
    assert span.attributes is not None
    assert span.attributes["http.route"] == "/test"
    assert span.resource.attributes["service.name"] == service_name
    assert span.resource.attributes["service.instance.id"] == service_name
    exporter_factory.assert_called_once_with(endpoint=f"{endpoint}/v1/traces")
    metric_exporter_factory.assert_called_once_with(endpoint=f"{endpoint}/v1/metrics")
    requests_instrumentor.return_value.instrument.assert_called_once()
    metrics_data = metric_reader.get_metrics_data()
    assert metrics_data is not None
    assert any(scope.metrics for resource in metrics_data.resource_metrics for scope in resource.scope_metrics)

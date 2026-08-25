from unittest.mock import patch

from flask import Flask
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from core.config import Config
from core.managers import telemetry_manager


def test_initialize_instruments_flask_requests(monkeypatch):
    endpoint = "http://collector:4318"
    monkeypatch.setattr(Config, "OTEL_EXPORTER_OTLP_ENDPOINT", endpoint)
    exporter = InMemorySpanExporter()
    metric_reader = InMemoryMetricReader()
    app = Flask(__name__)
    app.get("/test")(lambda: "ok")

    with (
        patch.object(telemetry_manager, "OTLPSpanExporter", return_value=exporter) as exporter_factory,
        patch.object(telemetry_manager, "OTLPMetricExporter") as metric_exporter_factory,
        patch.object(telemetry_manager, "BatchSpanProcessor", SimpleSpanProcessor),
        patch.object(telemetry_manager, "PeriodicExportingMetricReader", return_value=metric_reader),
    ):
        telemetry_manager.initialize(app)
        response = app.test_client().get("/test")

    spans = exporter.get_finished_spans()
    assert response.status_code == 200
    assert len(spans) == 1
    span = spans[0]
    assert span.attributes is not None
    assert span.attributes["http.route"] == "/test"
    assert span.resource.attributes["service.name"] == "taranis-core"
    assert span.resource.attributes["service.instance.id"] == "taranis-core"
    exporter_factory.assert_called_once_with(endpoint=f"{endpoint}/v1/traces")
    metric_exporter_factory.assert_called_once_with(endpoint=f"{endpoint}/v1/metrics")
    metrics_data = metric_reader.get_metrics_data()
    assert metrics_data is not None
    assert any(scope.metrics for resource in metrics_data.resource_metrics for scope in resource.scope_metrics)

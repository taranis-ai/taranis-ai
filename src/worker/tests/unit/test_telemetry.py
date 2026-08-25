from types import SimpleNamespace
from unittest.mock import patch

import pytest
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from worker import telemetry
from worker.config import Config


def test_disabled_telemetry_does_not_retry_failed_job(monkeypatch):
    monkeypatch.setattr(Config, "OTEL_EXPORTER_OTLP_ENDPOINT", None)
    calls = 0

    @telemetry.instrument_job
    def failed_job():
        nonlocal calls
        calls += 1
        raise RuntimeError("failed")

    with pytest.raises(RuntimeError, match="failed"):
        failed_job()

    assert calls == 1


def test_instrument_job_exports_trace_and_metrics(monkeypatch):
    endpoint = "http://telemetry:4318"
    parent_span_id = "00f067aa0ba902b7"
    monkeypatch.setattr(Config, "OTEL_EXPORTER_OTLP_ENDPOINT", endpoint)
    monkeypatch.setattr(telemetry, "_tracer_provider", None)
    monkeypatch.setattr(telemetry, "_meter_provider", None)
    monkeypatch.setattr(telemetry, "_tracer", None)
    monkeypatch.setattr(telemetry, "_completed_jobs", None)
    monkeypatch.setattr(telemetry, "_job_duration", None)
    monkeypatch.setattr(
        telemetry,
        "get_current_job",
        lambda: SimpleNamespace(
            id="job-1",
            origin="bots",
            func_name="worker.bots.bot_tasks.bot_task",
            meta={"traceparent": f"00-4bf92f3577b34da6a3ce929d0e0e4736-{parent_span_id}-01"},
        ),
    )
    span_exporter = InMemorySpanExporter()
    metric_reader = InMemoryMetricReader()

    with (
        patch.object(telemetry, "OTLPSpanExporter", return_value=span_exporter) as span_exporter_factory,
        patch.object(telemetry, "OTLPMetricExporter") as metric_exporter_factory,
        patch.object(telemetry, "BatchSpanProcessor", SimpleSpanProcessor),
        patch.object(telemetry, "PeriodicExportingMetricReader", return_value=metric_reader),
    ):

        @telemetry.instrument_job
        def example_job():
            return "done"

        assert example_job() == "done"

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].parent is not None
    assert spans[0].parent.span_id == int(parent_span_id, 16)
    assert spans[0].attributes is not None
    assert spans[0].attributes["messaging.destination.name"] == "bots"
    assert spans[0].attributes["rq.job.status"] == "success"
    assert spans[0].resource.attributes["service.name"] == "taranis-worker"
    span_exporter_factory.assert_called_once_with(endpoint=f"{endpoint}/v1/traces", timeout=0.5)
    metric_exporter_factory.assert_called_once_with(endpoint=f"{endpoint}/v1/metrics", timeout=0.5)

    metrics_data = metric_reader.get_metrics_data()
    assert metrics_data is not None
    metric_names = {metric.name for resource in metrics_data.resource_metrics for scope in resource.scope_metrics for metric in scope.metrics}
    assert metric_names == {"taranis.worker.job.duration", "taranis.worker.jobs"}

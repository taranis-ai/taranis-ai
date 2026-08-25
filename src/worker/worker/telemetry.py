from collections.abc import Callable
from functools import wraps
from time import perf_counter
from typing import ParamSpec, TypeVar

from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.metrics import Counter, Histogram
from opentelemetry.propagate import extract
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Tracer
from rq import get_current_job

from worker.config import Config
from worker.log import logger


P = ParamSpec("P")
R = TypeVar("R")

_tracer_provider: TracerProvider | None = None
_meter_provider: MeterProvider | None = None
_tracer: Tracer | None = None
_completed_jobs: Counter | None = None
_job_duration: Histogram | None = None
_EXPORT_TIMEOUT_MILLIS = 500


def _initialize() -> bool:
    global _tracer_provider, _meter_provider, _tracer, _completed_jobs, _job_duration

    if _tracer is not None:
        return True
    if not (endpoint := Config.OTEL_EXPORTER_OTLP_ENDPOINT):
        return False

    service_name = "taranis-worker"
    resource = Resource.create({SERVICE_NAME: service_name, "service.instance.id": service_name})
    _tracer_provider = TracerProvider(resource=resource)
    _tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces", timeout=_EXPORT_TIMEOUT_MILLIS / 1_000))
    )
    _meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[
            PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics", timeout=_EXPORT_TIMEOUT_MILLIS / 1_000),
                export_interval_millis=Config.OTEL_METRIC_EXPORT_INTERVAL,
            )
        ],
    )
    _tracer = _tracer_provider.get_tracer("taranis-worker")
    meter = _meter_provider.get_meter("taranis-worker")
    _completed_jobs = meter.create_counter("taranis.worker.jobs", description="Completed RQ jobs")
    _job_duration = meter.create_histogram("taranis.worker.job.duration", unit="s", description="RQ job duration")
    return True


def instrument_job[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            enabled = _initialize()
        except Exception as exc:
            logger.warning(f"Failed to initialize OpenTelemetry: {exc}")
            return func(*args, **kwargs)
        if not enabled:
            return func(*args, **kwargs)

        tracer = _tracer
        completed_jobs = _completed_jobs
        job_duration = _job_duration
        tracer_provider = _tracer_provider
        meter_provider = _meter_provider
        assert tracer is not None
        assert completed_jobs is not None
        assert job_duration is not None
        assert tracer_provider is not None
        assert meter_provider is not None

        job = get_current_job()
        queue = str(job.origin) if job and job.origin else "unknown"
        job_id = str(job.id) if job and job.id else "unknown"
        task = job.func_name if job and job.func_name else f"{func.__module__}.{func.__name__}"
        parent_context = extract(job.meta or {}) if job else None
        span_attributes = {
            "messaging.system": "redis",
            "messaging.destination.name": queue,
            "messaging.operation.name": "process",
            "messaging.message.id": job_id,
            "rq.job.function": task,
        }
        metric_attributes = {"queue": queue, "task": task}
        status = "success"
        started = perf_counter()

        try:
            with tracer.start_as_current_span(task, context=parent_context, kind=SpanKind.CONSUMER, attributes=span_attributes) as span:
                try:
                    return func(*args, **kwargs)
                except Exception:
                    status = "failure"
                    raise
                finally:
                    span.set_attribute("rq.job.status", status)
        finally:
            metric_attributes["status"] = status
            try:
                completed_jobs.add(1, metric_attributes)
                job_duration.record(perf_counter() - started, metric_attributes)
                tracer_provider.force_flush(timeout_millis=_EXPORT_TIMEOUT_MILLIS)
                meter_provider.force_flush(timeout_millis=_EXPORT_TIMEOUT_MILLIS)
            except Exception as exc:
                logger.warning(f"Failed to export OpenTelemetry data: {exc}")

    return wrapper

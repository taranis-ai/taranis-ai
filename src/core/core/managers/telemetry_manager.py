from typing import Any

import sentry_sdk
from flask import Flask
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from core.config import Config


def initialize(app: Flask):
    _initialize_sentry()
    _initialize_opentelemetry(app)


def _initialize_sentry():
    if not (dsn := Config.TARANIS_CORE_SENTRY_DSN):
        return

    sentry_options: dict[str, Any] = {
        "dsn": dsn,
        "traces_sample_rate": 1.0,
        "profiles_sample_rate": 1.0,
    }
    if Config.SENTRY_ENABLE_LOGS:
        sentry_options["enable_logs"] = True
    if Config.SENTRY_SEND_DEFAULT_PII:
        sentry_options["send_default_pii"] = True
    if Config.SENTRY_ENABLE_DB_QUERY_SOURCE:
        sentry_options["enable_db_query_source"] = True

    sentry_sdk.init(**sentry_options)


def _initialize_opentelemetry(app: Flask):
    if not (endpoint := Config.OTEL_EXPORTER_OTLP_ENDPOINT):
        return

    service_name = "taranis-core"
    resource = Resource.create({SERVICE_NAME: service_name, "service.instance.id": service_name})
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")))
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[
            PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics"),
                export_interval_millis=Config.OTEL_METRIC_EXPORT_INTERVAL,
            )
        ],
    )
    FlaskInstrumentor().instrument_app(app, tracer_provider=tracer_provider, meter_provider=meter_provider)

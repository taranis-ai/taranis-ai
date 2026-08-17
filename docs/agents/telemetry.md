# Telemetry

## When To Load
OpenTelemetry, OTLP, Sentry, Grafana LGTM, Flask instrumentation, RQ job traces, worker metrics, or trace-context propagation.

## Expected Behavior
Sentry and OpenTelemetry are optional. Core and frontend initialize every configured telemetry integration through one component-level entry point. A normalized `OTEL_EXPORTER_OTLP_ENDPOINT` base URL enables OTLP/HTTP traces and metrics; no endpoint disables both. Core and frontend emit Flask request metrics and spans. Frontend calls to core remain in the incoming trace. RQ jobs continue that trace and emit bounded completed-job and duration metrics.

The bundled Grafana LGTM service is opt-in through the `telemetry` Compose profile. External OTLP backends remain supported by configuring their base URL without enabling the profile.

## Code Paths
- Core configuration and initialization: `src/core/core/config.py`, `src/core/core/managers/telemetry_manager.py`
- Frontend configuration and initialization: `src/frontend/frontend/config.py`, `src/frontend/frontend/setup.py`
- Core-to-RQ propagation: `src/core/core/managers/queue_manager.py`
- Worker job instrumentation and propagation: `src/worker/worker/telemetry.py`, `src/worker/worker/core_api.py`, `src/worker/worker/bot_api.py`
- Deployment: `docker/compose.yml`, `docker/compose-variations/`, `dev/compose.yml`

## Data Flow
Frontend Flask spans inject W3C trace context into requests to core. Core request spans inject that context into RQ job metadata. The decorated worker task extracts it, creates a consumer span, records job metrics, and flushes providers before RQ exits the forked or spawned work-horse process. Worker API clients inject the active context into calls back to core.

OTLP/HTTP uses the configured base URL plus the standard `/v1/traces` and `/v1/metrics` signal paths. `OTEL_EXPORTER_OTLP_HEADERS` and `OTEL_METRIC_EXPORT_INTERVAL` are read by the OpenTelemetry exporters.

## Testing
Run the focused telemetry and settings tests in core, frontend, and worker, then each component's full pytest and Ruff checks. Render every changed Compose file with `docker compose config`. For an integration smoke test, start the `telemetry` profile, exercise a frontend request and an RQ job, then verify the `taranis-frontend`, `taranis-core`, and `taranis-worker` resources in Grafana.

## Pitfalls
RQ executes jobs in short-lived forked or spawned work-horse processes that terminate with `os._exit`; worker telemetry must flush after each job. Keep that flush bounded so an unavailable backend cannot stall a completed job indefinitely. Do not initialize exporter threads only in the long-lived RQ polling process. Keep metric labels bounded to queue, task function, and status. Do not place credentials, arguments, job results, source content, or report content in span attributes or metric labels.

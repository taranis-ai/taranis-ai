# Telemetry

Load for: OpenTelemetry, OTLP, Sentry, Grafana LGTM, Flask instrumentation, RQ job traces, worker metrics, or trace-context propagation.

## Contracts

Sentry and OpenTelemetry are optional. Core and frontend initialize every configured telemetry integration through one component-level entry point. A normalized `OTEL_EXPORTER_OTLP_ENDPOINT` base URL enables OTLP/HTTP traces and metrics; no endpoint disables both. Each component's `OTEL_SERVICE_NAME` setting controls its OpenTelemetry service resource name and defaults to `taranis-core`, `taranis-frontend`, or `taranis-worker`. Each telemetry initialization generates a UUID for `service.instance.id`, shared by its traces and metrics. Worker initialization runs in the RQ work-horse process. Core and frontend emit Flask request metrics and spans. Frontend calls to core remain in the incoming trace. RQ jobs continue that trace and emit bounded completed-job and duration metrics.

The bundled Grafana LGTM service is opt-in through the `telemetry` Compose profile. Grafana and OTLP host ports bind to loopback only in every Compose variant. Remote Grafana exposure requires a unique password, TLS, and access controls; existing volumes require a password change in Grafana. External OTLP backends remain supported by configuring their base URL without enabling the profile.

## Code Paths

- Core configuration and initialization: `src/core/core/config.py`, `src/core/core/managers/telemetry_manager.py`
- Frontend configuration and initialization: `src/frontend/frontend/config.py`, `src/frontend/frontend/setup.py`
- Core-to-RQ propagation: `src/core/core/managers/queue_manager.py`
- Worker job instrumentation and propagation: `src/worker/worker/telemetry.py`, `src/worker/worker/core_api.py`, `src/worker/worker/bot_api.py`
- Deployment: `docker/compose.yml`, `docker/compose-variations/`, `dev/compose.yml`

## Data Flow

Frontend Flask spans inject W3C trace context into requests to core. Core request spans inject that context into RQ job metadata. The decorated worker task extracts it, creates a consumer span, records job metrics, and flushes providers before RQ exits the forked or spawned work-horse process. Worker API clients inject the active context into calls back to core.

OTLP/HTTP uses the configured base URL plus the standard `/v1/traces` and `/v1/metrics` signal paths. `OTEL_EXPORTER_OTLP_HEADERS` and `OTEL_METRIC_EXPORT_INTERVAL` are read by the OpenTelemetry exporters.

## Coverage

The local test pipeline clears `OTEL_EXPORTER_OTLP_ENDPOINT`. Worker pytest setup also clears it before loading worker configuration, overriding inherited settings and the local `.env`. Core and frontend use their test `.env` files with an empty endpoint. Telemetry-specific tests enable instrumentation explicitly with in-memory exporters; ordinary tests must not contact a telemetry collector.

Render every changed Compose file with `docker compose config`. For an integration smoke test, start the `telemetry` profile, exercise a frontend request and an RQ job, then verify the `taranis-frontend`, `taranis-core`, and `taranis-worker` resources in Grafana.

## Pitfalls

RQ work-horses terminate with `os._exit`: initialize telemetry there and flush each job, splitting a one-second budget between traces and metrics. Align network timeouts because SDK flush deadlines may not be enforced. Bound labels to queue, task function, and status; never include credentials, arguments, results, or source/report content.

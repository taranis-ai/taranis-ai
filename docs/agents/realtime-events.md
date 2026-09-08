# Realtime Events

## When To Load

Centrifugo/SSE, `/sse`, connect proxy, `REALTIME_ENABLED`, reconnects, broadcasts/presence, preview/render completion, or report locks.

## Transport and Security

- Centrifugo uses rolling `v6.9` images across Compose/Kubernetes/Helm and existing Redis with prefix `taranis:realtime`. `REALTIME_ENABLED=false` disables publication/EventSource without affecting REST. Generic Docker samples default off until credentials are supplied; core has no usable default secrets.
- Public same-origin `${TARANIS_BASE_PATH}sse` proxies only to `/connection/uni_sse`, forwarding cookie/origin with buffering/cache disabled. Client transport stays deployment-internal; API/health/metrics use a separate internal port. Never proxy admin/debug/Swagger/WebSocket or management endpoints publicly.
- Exact space-separated origin allowlists are enforced by Centrifugo before the core connect proxy. `POST ${TARANIS_BASE_PATH}api/realtime/connect` requires its dedicated secret plus a valid access cookie (type, expiry, revocation, current user) and returns global/organization/user channels. Authentication failure is terminal.
- EventSource cannot add custom headers. Keep proxy authentication separate from browser CSRF and use distinct API, JWT, Centrifugo API, and proxy secrets. Never put credentials in SSE URLs.
- Development-only exception: client/authenticated admin UI binds `0.0.0.0`, API/health stays loopback; proxy reaches host Core via `host.containers.internal`/`TARANIS_CORE_PORT`. Preserve `admin.external` behavior in `dev/compose.yml`.

## Delivery and Recovery

Core publishes small UUIDv7/versioned envelopes after domain commits through fixed global/organization/user methods and internal `/api/broadcast`. Use IDs/status, not domain payloads. The pooled HTTP client uses 200 ms connect/300 ms read timeouts and no retries. Network, HTTP, malformed, and top-level/per-channel Centrifugo errors (even HTTP 200) return false without changing domain success.

One frontend module owns one EventSource per authenticated tab, validates version/type, and emits `realtime:<event-type>`. Terminal disconnects stop; temporary failures retry eight times with jittered exponential backoff capped at 60 seconds and show one degraded notice after 15 seconds. Successful connection resets the budget; logout/teardown closes it.

Reconnect recovery coalesces authoritative-state refresh into `realtime:resync` after 300 ms. Control/heartbeat frames do not imply data changes. No broker history or Last-Event-ID replay is assumed. Assess/Analyze/Publish show a refresh notice; Assess refetches the filtered `#assess` fragment or navigates normally and retains its top bar/counter on empty results.

Terminal user source previews publish source ID/status only. Matching waiting fragments refetch HTML; retain reconnect and the existing 20-second fallback because delivery is best-effort. This is an explicit exception to the [general event-driven UI rule](frontend-development.md).

## Broadcasts, Presence, and Locks

- `ADMIN_OPERATIONS` may broadcast up to 500 characters on `global:events`. Render the exact message as text until dismissed and record it in [Notification Center](notification-center.md). Its audience is every connected user; never include restricted content.
- Presence is enabled only on `global`. Core queries `global:events`, resolves IDs to usernames, and returns client/unique-user counts to Admin Notifications. Do not grant client presence access or attach profile metadata; presence adds work proportional to connections.
- Report locks remain process-local, serialized with a thread lock; they provide no distributed leases, expiry, ownership tokens, or lost-update protection.

## Entry Points and Coverage

Core: `src/core/core/managers/realtime_publisher.py`, `src/core/core/api/realtime.py`, `src/core/core/managers/report_item_lock_service.py`. Browser: `src/frontend/frontend/static/js/realtime.js`, `src/frontend/frontend/templates/partials/realtime_notices.html`. Deployment: `src/ingress/extras/default.conf.template`, `dev/nginx.conf`, `docker/compose.yml`, `deploy/kubernetes/`, `deploy/helm/`.

Tests: `src/core/tests/unit/test_realtime_publisher.py`, `src/core/tests/unit/test_report_item_lock_service.py`, `src/core/tests/application/mixed_flows/security/test_realtime_connect.py`, `src/core/tests/application/worker_pipeline/test_worker_api.py`, `src/core/tests/application/user_workspace/assessment/test_assess_api.py`, `src/core/tests/test_schema.py`, `src/frontend/tests/unit/views/test_admin_notification_view.py`, `src/frontend/tests/playwright/test_realtime_js.py`.

General Docker-backed frontend E2E disables realtime because its stack has no Centrifugo. For deployment changes, render affected Compose variants, `helm template`, and `kubectl kustomize deploy/kubernetes`; start the configured image from rendered environments and verify health/authenticated broadcast. Browser-module tests alone do not validate the broker.

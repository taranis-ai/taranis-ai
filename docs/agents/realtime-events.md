# Realtime Events

## When To Load

Centrifugo, SSE, `/sse`, `/connection/uni_sse`, realtime events, `EventSource`, reconnect recovery, `REALTIME_ENABLED`, the realtime connect proxy, admin broadcasts, connected-client presence, report-lock notifications, or product-render completion.

## Expected Behavior

- Centrifugo `v6.9.1` is the only realtime broker. The image tag is pinned in Compose, raw Kubernetes, and the existing Helm chart.
- Browsers use the same-origin public `${TARANIS_BASE_PATH}sse` URL. NGINX rewrites only that route to Centrifugo's `/connection/uni_sse`, forwards authentication/origin headers, and disables buffering and caching.
- Centrifugo's client port is internal to the deployment. Its API, health, and metrics handlers use a separate internal port; admin, debug, Swagger, WebSocket, health, and metrics routes are not proxied publicly.
- Centrifugo uses the existing Redis instance with the dedicated `taranis:realtime` prefix.
- `REALTIME_ENABLED=false` prevents core publication and frontend `EventSource` creation without affecting REST behavior. The generic Docker sample keeps realtime disabled until dedicated credentials are supplied, and core has no usable default Centrifugo secrets.
- Core's fixed publisher methods send small, versioned envelopes to explicit global, organization, or user-limited channels. Call sites pass IDs and status only. Publication uses a pooled HTTP session, a dedicated API key, 200 ms connect and 300 ms read timeouts, and the HTTP client's default no-retry behavior.
- Realtime publication is best-effort. Any network, HTTP, malformed-response, or Centrifugo error returns false and cannot roll back or change the domain operation.
- Centrifugo enforces its exact browser-origin allowlist before calling the protected `POST ${TARANIS_BASE_PATH}api/realtime/connect` endpoint. Core requires the dedicated static proxy secret and a valid non-revoked access cookie before returning global, organization, and user channels. Authentication failures return a terminal Centrifugo disconnect.
- One frontend module owns one `EventSource` per authenticated tab. It checks the event version and type, dispatches domain events, coalesces reconnect resynchronization for 300 ms, closes on logout/teardown, and never starts a polling loop.
- Centrifugo connection, heartbeat, and other control frames do not trigger resynchronization. Terminal disconnects stop reconnection; temporary failures reconnect with jitter and show one degraded notice after 15 seconds.
- Relevant Assess, Analyze, and Publish pages show one refresh notice for domain events and reconnect resynchronization. Assess reloads its current filtered `#assess` fragment through HTMX when available and falls back to normal navigation.
- A terminal OSINT source preview publishes a user-scoped event. The matching waiting fragment immediately refetches its authoritative HTML through HTMX; reconnect resynchronization and the existing 20-second trigger remain fallbacks for missed or disabled realtime delivery.
- Administrators with `ADMIN_OPERATIONS` can send a message of up to 500 characters from the dedicated Admin Notifications page. Core publishes the exact string as a persistent `notification.broadcast` event on `global:events`; each connected browser renders it as text until manually dismissed and records it in the browser-session Notification Center.
- Presence is enabled only for the `global` namespace. The Admin Notifications page asks core for server-side `global:events` presence, shows connected client and unique-user counts, and resolves Centrifugo user IDs to Taranis usernames. Clients are not granted permission to query presence, and organization/user namespaces keep presence disabled.
- Development Compose publishes Centrifugo's client and authenticated admin UI port on `0.0.0.0`, while its API and health port stays on loopback. Keep this development-only split and `admin.external` behavior when changing `dev/compose.yml`.
- The report-lock compatibility service serializes its process-local state with one thread lock. Redis leases, ownership tokens, expiry, and lost-update protection are out of scope and will be implemented in the next PR.

## Code Paths

- Core configuration: `src/core/core/config.py`
- Publisher and channel/event contracts: `src/core/core/managers/realtime_publisher.py`
- Connect proxy, admin broadcast, and connected-client endpoints: `src/core/core/api/realtime.py`
- Report lock compatibility service: `src/core/core/managers/report_item_lock_service.py`
- Domain publishers: `src/core/core/api/assess.py`, `analyze.py`, `bots.py`, `connectors.py`, `worker.py`, `src/core/core/service/report_publish_workflow.py`, and `task.py`
- OSINT source preview consumer: `src/frontend/frontend/templates/osint_source/osint_source_preview.html`
- Frontend connection module: `src/frontend/frontend/static/js/realtime.js`
- Frontend realtime notices: `src/frontend/frontend/templates/partials/realtime_notices.html`
- Admin Notifications view and template: `src/frontend/frontend/views/admin_views/notification_views.py`, `src/frontend/frontend/templates/admin_notifications/index.html`
- Frontend gate and URL: `src/frontend/frontend/config.py` and `templates/base.html`
- NGINX route: `src/ingress/extras/default.conf.template` and `dev/nginx.conf`
- Centrifugo environment configuration: `docker/compose.yml`, `deploy/kubernetes/00-config.yaml`, and `deploy/helm/templates/configmap.yaml`
- Deployment shapes: `docker/compose.yml`, `docker/compose-variations/`, `deploy/kubernetes/`, and `deploy/helm/`

## Data Flow

After a successful domain mutation, committed presenter result, or validated admin broadcast, core creates one UUIDv7 event envelope and calls Centrifugo's cluster-internal `/api/broadcast` endpoint. Centrifugo distributes the publication through Redis to connected clients on the resolved channel. The browser connects through NGINX; Centrifugo calls core's connect proxy with the forwarded cookie and origin plus its static proxy secret. The frontend checks received publication data and emits `realtime:<event-type>`. After a lost connection reopens, it emits one debounced `realtime:resync` so active page code can fetch authoritative state. Separately, an authorized Admin Notifications page load calls core, core queries `/api/presence` for `global:events`, and core joins the returned user IDs with the Taranis user table before returning the admin-only status response.

When a worker persists a terminal `source_preview_<source_id>` task for a user, core publishes only the source ID and status. The matching preview page treats that event as an invalidation and refetches the existing server-rendered fragment; preview data never travels through SSE.

## Testing

- Publisher and envelope contract: `cd src/core && uv run pytest tests/unit/test_realtime_publisher.py`
- Assess mutation publication and report-lock serialization: `cd src/core && uv run pytest tests/application/user_workspace/assessment/test_assess_api.py tests/unit/test_report_item_lock_service.py`
- Preview publication and fragment trigger: `cd src/core && uv run pytest tests/application/worker_pipeline/test_worker_api.py`; `cd src/frontend && uv run pytest tests/unit/views/test_views.py tests/playwright/test_realtime_js.py --e2e-ci`
- Connect proxy, broadcast, presence, and OpenAPI security: `cd src/core && uv run pytest tests/application/mixed_flows/security/test_realtime_connect.py tests/test_schema.py`
- Admin Notifications page: `cd src/frontend && uv run pytest tests/unit/views/test_admin_notification_view.py`
- Browser module: `cd src/frontend && uv run pytest tests/playwright/test_realtime_js.py --e2e-ci`
- Render Compose variants with `docker compose ... config`.
- Render the chart with `helm template` and raw manifests with `kubectl kustomize deploy/kubernetes`.
- Start the pinned Centrifugo image from each rendered environment and verify health plus an authenticated broadcast; Centrifugo validates environment configuration on startup.

## Pitfalls

- Never reuse `API_KEY`, `JWT_SECRET_KEY`, the Centrifugo HTTP API key, or the connect-proxy secret for another role.
- Do not put access tokens or API keys in the public SSE URL or logs.
- Treat broadcast text as public to every connected user in the instance. Render it only through `textContent`, never HTML, and do not include secrets or audience-restricted information.
- Global-channel presence adds broker and Redis work proportional to active connections. Keep it limited to the one global namespace, query it only from core, and do not add client presence permissions or connection metadata containing profile data.
- A Centrifugo HTTP 200 may still contain a top-level or per-channel API error; validate the response body.
- Native `EventSource` cannot add custom headers. Centrifugo enforces the browser origin, while Core authenticates the forwarded same-origin cookie and server-to-server proxy secret.
- Do not remove the preview's polling fallback unless realtime delivery becomes durable; publication is best-effort and Centrifugo history is disabled.
- Allowed origins are exact, space-separated values. Do not add wildcard fallback behavior.
- Keep `/api`, `/health`, `/metrics`, `/debug`, `/admin`, and Swagger off the public realtime NGINX location.
- Reconnect recovery refetches authoritative state; no Centrifugo history or `Last-Event-ID` replay is assumed.
- Do not extend the compatibility report-lock service in this PR; the distributed lease redesign belongs to the next PR.

# Realtime Events

## When To Load

Centrifugo, SSE, `/sse`, `/connection/uni_sse`, realtime events, `EventSource`, reconnect recovery, `REALTIME_ENABLED`, the realtime connect proxy, report-lock notifications, or product-render completion.

## Expected Behavior

- Centrifugo `v6.9.1` is the only realtime broker. The image tag is pinned in Compose, raw Kubernetes, and the existing Helm chart.
- Browsers use the same-origin public `${TARANIS_BASE_PATH}sse` URL. NGINX rewrites only that route to Centrifugo's `/connection/uni_sse`, forwards authentication/origin headers, and disables buffering and caching.
- Centrifugo's client port is internal to the deployment. Its API, health, and metrics handlers use a separate internal port; admin, debug, Swagger, WebSocket, health, and metrics routes are not proxied publicly.
- Centrifugo uses the existing Redis instance with the dedicated `taranis:realtime` prefix.
- `REALTIME_ENABLED=false` prevents core publication and frontend `EventSource` creation without affecting REST behavior.
- Core's fixed publisher methods send small, versioned envelopes to explicit global, organization, or user-limited channels. Call sites pass IDs and status only. Publication uses a pooled HTTP session, a dedicated API key, 200 ms connect and 300 ms read timeouts, and the HTTP client's default no-retry behavior.
- Realtime publication is best-effort. Any network, HTTP, malformed-response, or Centrifugo error returns false and cannot roll back or change the domain operation.
- The connect proxy is reachable by Centrifugo directly on core but blocked at public NGINX. It requires its dedicated static proxy secret, an exact allowed `Origin`, and a valid non-revoked access cookie before returning global, organization, and user channels. Authentication failures return a terminal Centrifugo disconnect.
- One frontend module owns one `EventSource` per authenticated tab. It checks the event version and type, dispatches domain events, coalesces reconnect resynchronization for 300 ms, closes on logout/teardown, and never starts a polling loop.
- Centrifugo connection, heartbeat, and other control frames do not trigger resynchronization. Terminal disconnects stop reconnection; temporary failures reconnect with jitter and show one degraded notice after 15 seconds.
- Relevant Assess, Analyze, and Publish pages show one refresh notice for domain events and reconnect resynchronization. Assess reloads its current filtered `#assess` fragment through HTMX when available and falls back to normal navigation.
- Development Compose publishes both Centrifugo ports on `0.0.0.0` so they remain reachable from the host when services run inside Podman Machine. Keep this development-only exposure when changing `dev/compose.yml`.
- The report-lock compatibility service intentionally preserves the existing process-local behavior in this PR. Redis leases, ownership tokens, expiry, and lost-update protection are out of scope and will be implemented in the next PR.

## Code Paths

- Core configuration: `src/core/core/config.py`
- Publisher and channel/event contracts: `src/core/core/managers/realtime_publisher.py`
- Connect proxy: `src/core/core/api/realtime.py`
- Report lock compatibility service: `src/core/core/managers/report_item_lock_service.py`
- Domain publishers: `src/core/core/api/assess.py`, `analyze.py`, `bots.py`, `connectors.py`, `worker.py`, `src/core/core/service/report_publish_workflow.py`, and `task.py`
- Frontend connection module: `src/frontend/frontend/static/js/realtime.js`
- Frontend realtime notices: `src/frontend/frontend/templates/partials/realtime_notices.html`
- Frontend gate and URL: `src/frontend/frontend/config.py` and `templates/base.html`
- NGINX route: `src/ingress/extras/default.conf.template` and `dev/nginx.conf`
- Centrifugo environment configuration: `docker/compose.yml`, `deploy/kubernetes/00-config.yaml`, and `deploy/helm/templates/configmap.yaml`
- Deployment shapes: `docker/compose.yml`, `docker/compose-variations/`, `deploy/kubernetes/`, and `deploy/helm/`

## Data Flow

After a successful domain mutation or committed presenter result, core creates one UUIDv7 event envelope and calls Centrifugo's cluster-internal `/api/broadcast` endpoint. Centrifugo distributes the publication through Redis to connected clients on the resolved channel. The browser connects through NGINX; Centrifugo calls core's connect proxy with the forwarded cookie and origin plus its static proxy secret. The frontend checks received publication data and emits `realtime:<event-type>`. After a lost connection reopens, it emits one debounced `realtime:resync` so active page code can fetch authoritative state.

## Testing

- Publisher and envelope contract: `cd src/core && uv run pytest tests/unit/test_realtime_publisher.py`
- Connect proxy security: `cd src/core && uv run pytest tests/application/mixed_flows/security/test_realtime_connect.py`
- Browser module: `cd src/frontend && uv run pytest tests/playwright/test_realtime_js.py --e2e-ci`
- Render Compose variants with `docker compose ... config`.
- Render the chart with `helm template` and raw manifests with `kubectl kustomize deploy/kubernetes`.
- Start the pinned Centrifugo image from each rendered environment and verify health plus an authenticated broadcast; Centrifugo validates environment configuration on startup.

## Pitfalls

- Never reuse `API_KEY`, `JWT_SECRET_KEY`, the Centrifugo HTTP API key, or the connect-proxy secret for another role.
- Do not put access tokens or API keys in the public SSE URL or logs.
- A Centrifugo HTTP 200 may still contain a top-level or per-channel API error; validate the response body.
- Native `EventSource` cannot add custom headers. Authentication depends on same-origin cookies forwarded by NGINX, while the server-to-server proxy secret prevents direct connect-proxy use.
- Allowed origins are exact, space-separated values. Do not add wildcard fallback behavior.
- Keep `/api`, `/health`, `/metrics`, `/debug`, `/admin`, and Swagger off the public realtime NGINX location.
- Reconnect recovery refetches authoritative state; no Centrifugo history or `Last-Event-ID` replay is assumed.
- Do not extend the compatibility report-lock service in this PR; the distributed lease redesign belongs to the next PR.

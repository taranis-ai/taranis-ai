# Realtime Events

Load for: Centrifugo/SSE, `/sse`, connect proxy, `REALTIME_ENABLED`, reconnects, broadcasts/presence, preview/render completion, or report locks.

## Transport and Security

- Centrifugo uses rolling `v6.9` images across Compose/Kubernetes/Helm and existing Redis with prefix `taranis:realtime`. `REALTIME_ENABLED=false` disables publication/EventSource without affecting REST. Generic Docker samples default off until credentials are supplied; core has no usable default secrets.
- Public same-origin `${TARANIS_BASE_PATH}sse` proxies only to `/connection/uni_sse`, forwarding cookie/origin with buffering/cache disabled. Client transport stays deployment-internal; API/health/metrics use a separate internal port. Never proxy admin/debug/Swagger/WebSocket or management endpoints publicly.
- Exact space-separated origin allowlists are enforced by Centrifugo before the core connect proxy. `POST ${TARANIS_BASE_PATH}api/realtime/connect` requires its dedicated secret plus a valid access cookie (type, expiry, revocation, current user) and returns global/organization/user channels. Authentication failure is terminal.
- EventSource cannot add custom headers. Keep proxy authentication separate from browser CSRF and use distinct API, JWT, Centrifugo API, and proxy secrets. Never put credentials in SSE URLs.
- Development-only exception: client/authenticated admin UI uses host port `8001` (leaving `8000` for inference) and binds `0.0.0.0`, API/health stays loopback; proxy reaches host Core via `host.containers.internal`/`TARANIS_CORE_PORT`. Docker requires the explicit `host.containers.internal:host-gateway` mapping in `dev/compose.yml`. Preserve `admin.external` behavior.

## Delivery and Recovery

Core publishes small UUIDv7/versioned envelopes after domain commits through fixed global/organization/user methods and internal `/api/broadcast`. Domain invalidations use IDs/status, not domain payloads; Analyst Chat is the sole content-bearing user event. The pooled HTTP client uses 200 ms connect/300 ms read timeouts and no retries. Network, HTTP, malformed, and top-level/per-channel Centrifugo errors (even HTTP 200) return false without changing domain success.

One frontend module owns one EventSource per authenticated tab, validates version/type, and emits `realtime:<event-type>`. Terminal disconnects stop; temporary failures retry eight times with jittered exponential backoff capped at 60 seconds and show one degraded notice after 15 seconds. Successful connection resets the budget; logout/teardown closes it. The shared transport sets `html[data-realtime-connected]` only after Centrifugo acknowledges the connection and clears it on disconnect/error/close. CSS hides `[data-realtime-fallback]` controls while connected; the document-root flag survives HTMX body restoration without page-specific listeners or requests.

Reconnect recovery coalesces authoritative-state refresh into `realtime:resync` after 300 ms. Control/heartbeat frames do not imply data changes. No broker history or Last-Event-ID replay is assumed. Assess/Analyze/Publish show a refresh notice; Assess refetches the filtered `#assess` fragment or navigates normally and retains its top bar/counter on empty results.

Terminal user source previews publish source ID/status only. Matching waiting fragments refetch HTML; retain reconnect and the 20-second fallback because delivery is best-effort. This is an explicit exception to the [general event-driven UI rule](frontend-development.md).

## Task Views

Scheduler state changes publish payload-free `scheduler.changed` on `global:events`; owned task changes additionally publish payload-free `task.changed` on the owner's `user:#<user_id>` channel. Scheduler fragments still enforce their existing permissions. Never include task identity, names, results, checkpoints, or exception text in these hints.

Core invalidates scheduler/task caches before publication after enqueues, cancellation, cron changes, committed results (including pipeline stages), and history removal. Purges match RQ identities against `Task.job_id` and retain affected owners before deleting records. Source toggles and bot deletion commit before changing cron registrations so notifications observe committed configuration.

Worker task entry decorators notify after RQ records `STARTED` on both fork and spawn platforms. Parent workers notify after execution settles (including retries and killed workhorses), and on worker birth/death. Cron enqueues and RQ delayed-job promotion notify after Redis commits through API-key-only `/api/worker/tasks/changed`. RQ lacks a scheduler-class option: `worker/task_events.py` retains its start/lock and enqueue semantics while publishing from the same promoted-job snapshot. Preserve this boundary when upgrading RQ. Worker notices have bounded timeouts, no retries, and preserve RQ deadline exceptions.

The views coalesce these events and `realtime:resync` into authoritative HTMX fragment reads, preserving active queries, without timed polling or full-page reloads. Initial connection also resynchronizes. Realtime delivery remains best-effort; disabled/failed connections use explicit refresh and reconnect recovery.

## Story Editor AI Results

Successful staged bot runs publish user-scoped `story.bot.finished` after commit and frontend cache invalidation, in one publication per saved result, regardless of story/stage count. Its `data.stories` maps story IDs to deduplicated bot types, without result content; rejected, failed, duplicate, and unattributed background runs do not publish these completion events. The Assess invalidation remains separate.

One form-free controller per story editor queues completion events and fetches the authenticated edit route once per matching event with supported bot types. OOB swaps update only affected summary/title, sentiment, classification, or tag displays. HTMX 4 trigger filters stop at the first `]`; use `Reflect.get` for story-map lookups.

Local events update saved tag baselines and merge completed bots’ generated attributes/markers. Preserve open tag editors, custom/unrelated drafts, comments, and item ordering. A completed field replaces a draft in that same field. Missed/disabled realtime requires reload; persisted results remain authoritative.

Coverage extends the bot-pipeline transaction test and the Assess browser workflow; the latter dispatches completion events because the isolated E2E stack has no broker.

## Analyst Chat

- `chat.turn.updated` carries turn ID, increasing sequence, stage, and cumulative text only on the owner’s `user:#<user_id>` channel. Accept only the newest matching turn; render via `textContent`. Never log snapshots or enable channel history/cache recovery.
- Publish stages immediately and text at most every 200 ms. First publish failure disables realtime for that turn without affecting generation/persistence. Later snapshots repair gaps; final synchronous HTMX is authoritative.

Producer and consumer: `src/core/core/service/chat.py`, `src/frontend/frontend/static/js/chat.js`.

## Broadcasts, Presence, and Locks

- `ADMIN_OPERATIONS` may broadcast up to 500 characters on `global:events`. Render the exact message as text until dismissed and record it in [Notification Center](notification-center.md). Its audience is every connected user; never include restricted content.
- Presence is enabled only on `global`. Core queries `global:events`, resolves IDs to usernames, and returns client/unique-user counts to Admin Notifications. Do not grant client presence access or attach profile metadata; presence adds work proportional to connections.
- Report locks remain process-local, serialized with a thread lock; they provide no distributed leases, expiry, ownership tokens, or lost-update protection.

## Code and Tests

Core: `src/core/core/managers/realtime_publisher.py`, `src/core/core/api/realtime.py`, `src/core/core/managers/report_item_lock_service.py`. Browser: `src/frontend/frontend/static/js/realtime.js`, `src/frontend/frontend/templates/partials/realtime_notices.html`. Deployment: `src/ingress/extras/default.conf.template`, `dev/nginx.conf`, `docker/compose.yml`, `deploy/kubernetes/`, `deploy/helm/`.

Tests: `src/core/tests/unit/test_realtime_publisher.py`, `src/core/tests/unit/test_report_item_lock_service.py`, `src/core/tests/application/mixed_flows/security/test_realtime_connect.py`, `src/core/tests/application/worker_pipeline/test_worker_api.py`, `src/core/tests/application/user_workspace/assessment/test_assess_api.py`, `src/core/tests/test_schema.py`, `src/frontend/tests/unit/views/test_admin_notification_view.py`, `src/frontend/tests/playwright/test_realtime_js.py`.

General Docker-backed frontend E2E disables realtime because its stack has no Centrifugo. For deployment changes, render affected Compose variants, `helm template`, and `kubectl kustomize deploy/kubernetes`; start the configured image from rendered environments and verify health/authenticated broadcast. Browser-module tests alone do not validate the broker.

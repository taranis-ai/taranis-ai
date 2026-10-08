# LLM Endpoints

## When To Load

Shared provider settings, Chat configuration, LLM bot execution, or endpoint health checks.

## Contracts

- **Admin Settings > LLM Endpoints** is available independently of `CHAT_ENABLED`. Named endpoints store base URL, model, API format, API key, and positive timeout in the singleton settings JSON. Names are unique ignoring case.
- Resolution order: bot `LLM_ENDPOINT`, feature assignment, shared default. Blank inherits; no default leaves unassigned features unconfigured. Titles share the summarization assignment. Core resolves Chat each turn and includes the effective provider in bot configuration once per run. `REQUESTS_TIMEOUT` overrides endpoint timeout; running jobs keep their starting configuration.
- Endpoint and assignment mutations lock the settings row. Deletion rejects default, feature, or bot references, including disabled bots; unknown IDs return 404. Bot selection shares the lock. Settings PATCH cannot replace the endpoint dictionary to bypass validation.
- Admin mutations require `ADMIN_OPERATIONS`. Human responses omit API keys and expose `api_key_configured`; blank preserves a key, explicit clear removes it. Only authenticated worker bot/configuration responses include raw credentials and use `Cache-Control: no-store`. Protect database access and backups.
- HTTP is supported for administrator-selected deployment networks. It sends credentials and content without encryption, including automatic checks of unassigned providers. Use HTTPS across untrusted networks.
- Startup ensures an endpoint at `http://llm-inference:8000/v1`, reusing one with that URL. New endpoints use Chat Completions and a blank model for the provider default. Startup refreshes its secret from `LLM_INFERENCE_API_KEY` (blank clears it), preserves saved model/API/timeout values and assignments, and selects it only when the shared default is empty. Deleting it causes recreation on restart. Deployment and rollback: [upgrade notes](../../deploy/README.md#shared-llm-endpoint-upgrade).
- Existing Chat provider settings become a Chat-only endpoint, preserving the destination without assigning background content to it. Conversion persists at initialization or the next settings write. Bot parameter compatibility belongs in [Worker Parameters](worker-parameters.md).
- Workers pass provider values explicitly to `taranis-llm-bot`; there is no environment fallback. Provider transport errors remain retryable `bot_service_unavailable`; missing configuration yields non-retryable `llm_not_configured`. Invalid input/output fails the job. Public errors are static; exception details stay in logs.
- NER produces entity tags using story cybersecurity mode; sentiment stores validated category/score attributes. Classification honors the threshold, stores item scores and aggregate story status, and skips empty item content. Summary/title updates use library schemas/prompts, change titles only for multiple news items, and mark successful story attributes. See [Story Clustering](story-clustering.md) for its reduced input.

## Endpoint checks

- Saving an endpoint or bot queues a synthetic inference through RQ; Core startup checks all saved endpoints, including unused ones. Checks exercise the selected API format, authentication, and model, contain no story content, and may incur provider usage.
- Failed checks retry after 10, 30, 120, and 300 seconds, subject to worker scheduling. After exhaustion, save the endpoint/bot or restart Core to recheck.
- Redis stores health separately from execution history. Each `check_id` identifies one scheduled check; saves/restarts replace it so delayed results are ignored. The configuration fingerprint also rejects results for changed settings. Deletion clears state. Worker configuration responses are non-cacheable; public status contains no credentials or provider error text.
- Pending/failed saved endpoints make `/health` return 503 with `worker_endpoints=down`; queues disabled means `n/a`. Container health tolerates endpoint-only degradation so administrators can repair configuration. Aggregate health and failure filters read each endpoint once rather than once per bot.
- Bot overview status prioritizes disabled, then failed/pending endpoint health, then last execution. Failed probes contribute to failure filters/menu counts; healthy probes clear only that failure. Completion invalidates settings, bots, menu badges, dashboard, and health caches.

## Entry Points and Coverage

- Validation: `src/models/models/llm.py`; persistence/resolution: `src/core/core/model/settings.py`; startup: `core/managers/db_seed_manager.py`.
- Boundaries: Core `api/settings.py`, `api/worker.py`; frontend settings view and `settings/llm.html`; worker `llm.py` and the five LLM bots.
- Health: Core `service/endpoint_health.py`, worker `endpoint_health.py`, `/worker/endpoint-health/<kind>/<id>`.
- Coverage: Core settings/admin API and health lifecycle workflows; Chat client suite; worker bot and endpoint-check workflows; frontend admin settings and full-stack RQ tests. Extend these workflows rather than adding duplicate orchestration tests.

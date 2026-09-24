# LLM Endpoints

## When To Load

Shared LLM settings, provider assignments, Chat configuration, clustering, or summary/title execution.

## Contracts

- Admin Settings always shows LLM Endpoints, independently of `CHAT_ENABLED`. Each named endpoint stores base URL, model, API format, API key, and positive timeout in the singleton settings JSON. No new tables or migration are required.
- Explicit Chat, clustering, or summarization assignment wins over the shared default. An empty assignment inherits the default; an empty default leaves unassigned features unconfigured. Titles use the summarization assignment. NER, sentiment, and classification still use the standalone bot service.
- Endpoint mutations and assignments lock the singleton settings row. Delete refuses endpoints used by a default or explicit assignment. Settings PATCH cannot bypass endpoint validation by replacing the endpoint dictionary. Endpoint names are unique ignoring case.
- Settings responses omit endpoint API keys and expose only `api_key_configured`. Blank retains an existing key; explicit clear removes it. Keys remain in the database, so protect database access/backups. Admin mutations require `ADMIN_OPERATIONS`; `/worker/llm-endpoints/<feature>` requires the service API key and sends `Cache-Control: no-store`.
- Old `chat_llm_*` values convert to `existing-chat`, assigned only to Chat. This avoids changing destinations for background content without an administrator choosing a default. Conversion persists during initialization or the next settings write.
- Core reads settings each Chat turn. Workers fetch the effective endpoint once per run and pass all provider values explicitly to the internal library; no worker `LLM_*` fallback, including when model is empty. `REQUESTS_TIMEOUT`, when set on a bot, overrides the endpoint timeout. A running job keeps its starting configuration.
- Provider errors retain retryable `bot_service_unavailable`; task errors remain static and suppress exception chains. Missing configuration persists a non-retryable `llm_not_configured` result directing the administrator to LLM Endpoints. Clustering keeps its reduced story payload. Summarization uses the library's summary/title schemas and prompts, updates a title only for multiple news items, and marks successful updates through the existing story attribute workflow.

## Entry Points and Coverage

- Shared validation: `src/models/models/llm.py`; persistence and resolution: `src/core/core/model/settings.py`.
- Admin/worker boundaries: `src/core/core/api/settings.py`, `src/core/core/api/worker.py`; frontend: settings view and `settings/llm.html`.
- Worker client/error boundary: `src/worker/worker/llm.py`; clustering and summary bots.
- Extend the admin API settings workflow for resolution, secrets, and deletion; the Chat client suite for both API formats; worker bot workflows for real library prompts/parsers; and `test_admin_settings` for create, validation recovery, assignment, reload, preserved keys, and deletion guards.

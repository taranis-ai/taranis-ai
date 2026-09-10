# Analyst Chat

## When To Load

Chat routes, `CHAT_ENABLED`, `chat_*` settings, provider integration, conversational Assess search, or conversation persistence/privacy.

## Contracts

- Disabled by default; requires `ASSESS_ACCESS`. Users access only their own conversations. History persists until deletion; disabling Chat preserves it.
- One shared prompt uses the configured API format: Responses calls `{chat_llm_base_url}/responses` with `store: false`; Chat Completions calls `{chat_llm_base_url}/chat/completions` with system/user messages and nested function tools. General questions receive plain text; story questions call `search_stories` once, then receive an answer with tools disabled. Responses continuations preserve initial output, including encrypted reasoning, and matching `function_call_output`; Chat Completions preserves the assistant message (including reasoning), followed by a matching tool message. Providers must support function calling. Reasoning is never displayed.
- Both API formats stream. Chat Completions assembles fragmented tool arguments and requires a successful finish reason plus `[DONE]`; truncated or length-limited completions fail. Rejection before content permits one retry without streaming. Invalid calls/filters or failed/partial streams fail the turn without saving messages; there is no repair loop.
- Search uses `AssessSearchFilters`, current-user ACL/TLP restrictions, and exact catalog/recent-story references. Lists require string arrays (`[]` when unused); unused scalars use JSON `null`. Reject text search `"null"` regardless of case/whitespace. Recent-story IDs combine only with sort. See [Assess Filters](assess-filters.md).
- Provider context includes the latest 10 saved messages, analyst timezone/current time, visible catalog, and accessible recent results. Search returns an authoritative total and at most `chat_max_stories` summaries containing ID, title, created time, and bounded summary/description. Use translated text alternatives for multilingual searches. Zero matches return a localized static answer without another provider call.
- Treat conversation/catalog/story content as untrusted. Never expose or log credentials, provider bodies, raw news content, inaccessible metadata, or exception-derived details. Invalid search arguments log a static warning.

## Persistence and Delivery

- A non-blocking Redis lease covers the owned conversation or the user's pending new conversation; overlap returns 409. Redis is required, realtime is optional; Chat runs in core independently of workers.
- One 540-second deadline covers the entire turn, including continuous response reads and persistence checks. Lease: 570 seconds; frontend timeout: 600 seconds; provider per-read timeout remains configurable.
- Roll back database work before outbound provider calls. Re-fetch the owned conversation and commit both messages together only after success. Store canonical filters, total count, and selected IDs as search metadata, never story text.
- Frontend escapes plain-text answers and builds the Assess link. Chat bypasses frontend model caching. Failed deletion retains the conversation.
- Cumulative realtime snapshots carry turn ID, increasing sequence, stage, and text on `user:#<user_id>`; text updates are throttled to 200 ms. Ignore other turns/older sequences. Final HTMX replaces transient content. Never log snapshots or enable channel history.

## Configuration

Only `CHAT_ENABLED` is deployment configuration. Flat `chat_*` settings in `core/model/settings.py` hold API format (`responses` by default, or `chat_completions`), URL, model, API key, timeout (120 seconds), and maximum stories (5; range 1–20). Validate before admin saves and initial seeding; read settings each turn.

For Mistral GLM-5.2, select **Chat Completions**, base URL `https://api.mistral.ai/v1`, model `zai-glm-5-2`, and a Mistral API key. URLs must omit the endpoint suffix. See [Mistral Chat API](https://docs.mistral.ai/api/endpoint/chat) and [model documentation](https://docs.mistral.ai/models/zai-glm-5-2). Existing settings keep Responses; no database migration is needed.

The separate Chat form patches submitted fields only. Serialized settings omit API keys; blank preserves the key, explicit clear removes it. Protect database/backups. Missing configuration returns the curated 503 setup warning through the conversation-list response, without exposing admin settings.

## Entry Points and Tests

- Core: `core/service/chat.py`, `core/model/chat.py`, `core/api/chat.py` under `src/core/`.
- Contracts: `src/models/models/chat.py`; new tables use startup metadata creation.
- Frontend: `frontend/views/chat_views.py`, `frontend/router/chat.py`, `frontend/templates/chat/`, `frontend/static/js/chat.js` under `src/frontend/`.
- Core tests: `src/core/tests/unit/test_chat_client.py`. Exercise both API formats through the same four feature flows: streamed general answer, persisted story search, no matches, and non-streaming fallback. Avoid provider-shape/negative-case matrices.
- Frontend tests: `src/frontend/tests/unit/views/test_chat_view.py`, `src/frontend/tests/playwright/test_realtime_js.py`.
- Validation/signoff: [Development Workflow](development-workflow.md).

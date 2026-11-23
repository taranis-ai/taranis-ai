# Analyst Chat

Load for: Chat routes, `CHAT_ENABLED`, `chat_*` settings, provider integration, conversational Assess search, or conversation persistence/privacy.

## Contracts

- Disabled by default; requires `ASSESS_ACCESS`. Users access only their own conversations. History persists until deletion; disabling Chat preserves it.
- One shared prompt uses the configured API format: Responses calls `{base_url}/responses` with `store: false`; Chat Completions calls `{base_url}/chat/completions` with system/user messages and nested function tools. General questions receive plain text; story questions call `search_stories` once, then receive an answer with tools disabled. Responses continuations preserve initial output, including encrypted reasoning, and matching `function_call_output`; Chat Completions preserves the assistant message (including reasoning), followed by a matching tool message. Providers must support function calling. Reasoning is never displayed.
- Both API formats stream. Chat Completions assembles fragmented tool arguments and requires a successful finish reason plus `[DONE]`; truncated or length-limited completions fail. Rejection before content permits one retry without streaming. Invalid calls/filters or failed/partial streams fail the turn without saving messages; there is no repair loop.
- Search uses `AssessSearchFilters`, current-user ACL/TLP restrictions, and exact catalog/recent-story references. The prompt requires omitting unused filters and forbids `null`, `"null"`, empty strings, and empty arrays. List filters use JSON arrays of strings; validation normalizes text search `"null"` to an unused value regardless of case/whitespace. Recent-story IDs combine only with sort. See [Assess Filters](assess-filters.md).
- Provider context includes the latest 10 saved messages, analyst timezone/current time, visible catalog, and accessible recent results. Search returns an authoritative total and at most `chat_max_stories` summaries containing ID, title, created time, and bounded summary/description. Use translated text alternatives for multilingual searches. Zero matches return a localized static answer without another provider call.
- Treat conversation/catalog/story content as untrusted. Never expose or log credentials, provider bodies, raw news content, inaccessible metadata, or exception-derived details. Invalid search arguments log a static warning.

## Persistence and Delivery

- A non-blocking Redis lease covers the owned conversation or the user's pending new conversation; overlap returns 409. Redis is required, realtime is optional; Chat runs in core independently of workers.
- One 540-second deadline covers the entire turn, including continuous response reads and persistence checks. Lease: 570 seconds; frontend timeout: 600 seconds; provider per-read timeout remains configurable.
- Shipped ingress and development Nginx give `/chat/` requests a 660-second read timeout so the synchronous POST can return final HTML and navigation headers. Separate realtime updates do not keep that POST alive. Recopy/reload installed development configs after changing `dev/nginx.conf`.
- Roll back database work before outbound provider calls. Re-fetch the owned conversation and commit both messages together only after success. Store canonical filters, total count, and selected IDs as search metadata, never story text.
- Frontend escapes answers, builds Assess links, bypasses model caching, and retains conversations on failed deletion. Starter prompts explain story searches and exclude administrative/system data.
- Saved messages use persisted UTC `created` through `format_datetime` with the user’s locale/timezone. Final responses and history share the template; unsaved placeholders have no timestamp.
- Cumulative realtime snapshots carry turn ID, increasing sequence, stage, and text on `user:#<user_id>`; text updates are throttled to 200 ms. Ignore other turns/older sequences. Final HTMX replaces transient content. Never log snapshots or enable channel history.

## Configuration

Set `CHAT_ENABLED=true` on Core and frontend to enable Chat. Configure its provider and assignment in **Admin Settings > LLM Endpoints**; Core resolves it each turn. **Admin Settings > Chat** controls `chat_max_stories` (default 5, range 1–20). See [LLM Endpoints](llm-endpoints.md) for provider, secret, and upgrade contracts.

The Chat form patches only submitted fields. Missing provider configuration returns a curated 503 setup warning through the conversation-list response without exposing admin settings.

## Code and Tests

- Core: `core/service/chat.py`, `core/model/chat.py`, `core/api/chat.py` under `src/core/`.
- Contracts: `src/models/models/chat.py`; new tables use startup metadata creation.
- Frontend: `frontend/views/chat_views.py`, `frontend/router/chat.py`, `frontend/templates/chat/`, `frontend/static/js/chat.js` under `src/frontend/`.
- Core tests: `src/core/tests/unit/test_chat_client.py`. Exercise both API formats through the shared feature flows: streamed general answer, persisted story search, and non-streaming fallback. Credential forwarding is asserted in the search flow; a socket-backed stream verifies deadline interruption and response cleanup. Avoid provider-shape/negative-case matrices.
- Frontend tests: `src/frontend/tests/unit/views/test_chat_view.py`, `src/frontend/tests/playwright/test_realtime_js.py`.
- Browser workflow: `test_e2e_workflow.py::TestUserWorkflow::test_chat` uses the scripted provider with real search/history, unread follow-up, and Assess evidence navigation. It cleans demo data, skips external instances, and uses shared highlights without fixed delays. Recording commands: Playwright README.

## HRAG turns

`HRAG_ENABLED` adds a per-turn mode selector and graph/vector evidence panels. Indexing requires `HRAG_ENABLED`. Administration > Settings > Chat sets `hrag_index_interval_minutes` (default 60; 0 means manual only) and exposes manual HRAG backfill and uncached status refresh through the admin-only `/admin/settings/hrag` frontend route; it uses the existing Core indexing API. Startup and settings saves do not start indexing; saving a changed interval updates the Redis schedule immediately. Indexing options apply on the next scheduled or manual pass. Relationship verification is optional (disabled by default); changing it creates a separate extraction generation, preserving the active index until replacement activation. The existing lease, deadline, atomic message save and streaming client remain shared. `core/service/hrag/` owns live authorization and indexing; `HragMessage` stores references and inherited evidence dependencies separately from Chat's search metadata. History rechecks references and withholds an answer if any supporting evidence is stale or inaccessible, including later Chat turns that used it. See [HRAG implementation](../../src/core/core/service/hrag/indexing.py) for deployment, generation controls and limits. Core uses llm-bot's transport-free prepared tasks through its existing HTTP transport; worker uses the library's inference extra.


Chat and HRAG share the existing `search_stories` filter-resolution call and validators; HRAG requires that call before retrieval. HRAG graph planning uses llm-bot’s `prepare_graph_query_generation()` for names/types/relationships/hops only. Its context excludes filter catalogs and search-result metadata. Core applies the Chat-resolved filters to both graph and vector retrieval, including vector fallback after a graph-planning failure. Invalid Chat filter resolution fails the turn without broadening retrieval. Final synthesis uses `prepare_hrag()` with current source IDs; `hrag/answering.py` decodes only the JSON answer field for streaming and validates citations before saving. HRAG structured output gets the library's one repair attempt under the shared deadline; ordinary Chat remains unchanged. Core suppresses llm-bot payload/repair diagnostics and reports static failures to avoid logging private provider output.

Semantic references always include a chunk index. `hrag_chunk_vector` is the only vector table; disabling chunking produces one chunk using the same claim, submission, ranking and citation path. Reconstruction uses frozen character-based splitting options and the current source fingerprint. ACL/TLP and Assess filters apply to the parent NewsItem before chunk ranking; runtime caps bound total chunks and chunks per item. Chat settings expose indexing options and activation of ready replacements. Both size increases and decreases rebuild independently of the active generation. LLM Endpoints configures dimensions per embedding model; blank inherits the server default. Dimensions are frozen in each generation, and query embeddings use the active generation’s dimensions until a replacement is activated.

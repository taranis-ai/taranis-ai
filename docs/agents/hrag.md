# HRAG

## When To Load

HRAG, graph RAG, pgvector, Apache AGE, embeddings, entity/relation extraction, or the `/api/hrag` route.

## Expected Behavior

`HRAG_BOT` is a normal post-collection bot. It sends each news item to the configured LLM bot for `/embed` and `/entity-relation-extraction`, while Core owns the embedding, extracted entities, evidence-backed relations, and the active graph schema. The seeded v1 schema covers cyber threat actors, malware, tools, vulnerabilities, organizations, and attacks. A user query queues `hrag_query_task`; it obtains an embedding and AGE Cypher from the LLM bot, asks Core for vector and graph context, then sends that context to `/hrag` for the answer.

For Docker Compose, set the bot's `BOT_ENDPOINT` to `http://llm-bot:<LLM_BOT_PORT>` (for example, `http://llm-bot:5008`).

## Code Paths

- Schema and persistence: `src/models/models/hrag.py`, `src/core/core/model/hrag.py`
- Post-collection bot: `src/worker/worker/bots/hrag_bot.py`
- Worker/Core boundary: `src/core/core/api/worker.py`, `src/worker/worker/core_api.py`
- User query and RQ task: `src/core/core/api/hrag.py`, `src/worker/worker/misc/hrag_tasks.py`
- Container image: `docker/database/Containerfile.hrag`

## Data Flow

Core schedules the bot after collection. The bot calls LLM-bot endpoints and submits only structured results to Core. Core writes the vector and relational evidence, then mirrors entities and relations into the `hrag` AGE graph. A query first gets ACL-filtered vector passages and evidence facts. Generated Cypher is executed only as a single, read-only AGE result value after Core safely renders its validated parameters; its rows are added as graph facts before the final LLM call. The worker sends only declared graph-schema fields and removes retrieval-only passage scores before calling the strict `/hrag` evidence contract.

## Testing

Run `cd src/core && uv run pytest tests/unit/test_hrag.py`, then run Ruff for the changed core, worker, and model files. AGE traversal requires PostgreSQL with the `age` extension; SQLite test runs exercise persistence and query validation but not AGE itself.

## Pitfalls

The worker API key is not an ACL bypass: vector retrieval is filtered using the requesting user's id passed in RQ metadata. AGE graph projection does not yet carry per-evidence ACL metadata, so Core intentionally disables broad AGE traversal while RBAC is enabled; relational facts tied to retrieved news items remain available. Query generation must return exactly one `agtype` expression aliased as `result`; all writes, comments, and multi-statement Cypher are rejected. The schema is persisted per instance; schema evolution requires a new immutable version and re-indexing rather than editing historical graph data in place.

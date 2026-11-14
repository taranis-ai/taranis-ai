# Hybrid retrieval in Chat

HRAG combines source-backed entity/relationship evidence from Neo4j Community with semantic matches from PostgreSQL/pgvector. Chat remains the default. Each turn can select **Chat** or **HRAG** within the same conversation. HRAG answers cite graph evidence (`[G1]`) and similar passages (`[V1]`); expandable panels link to the current stories in Assess.

## Enable

HRAG requires PostgreSQL, a Neo4j database dedicated to this Taranis installation, the normal Redis/RQ worker, and cron for ongoing reconciliation. For container deployments, set `CHAT_ENABLED=true` and a strong `HRAG_NEO4J_PASSWORD`, then add `docker/compose.hrag.yml` to the normal Compose command. The overlay enables HRAG on Core/frontend, adds Neo4j, and uses the pgvector PostgreSQL 18 image. Verify that the existing PostgreSQL major version matches before switching images; follow the normal PostgreSQL upgrade process otherwise. Do not reuse a database volume across major versions.

For host development, use `dev/compose.hrag.yml` with `dev/compose.yml`, set `CHAT_ENABLED=true` and `HRAG_ENABLED=true` on Core/frontend, and set Core's `HRAG_NEO4J_URI=bolt://127.0.0.1:7687`, `HRAG_NEO4J_USER=neo4j`, and `HRAG_NEO4J_PASSWORD`. Enable the existing cron process (`WITH_CRON_RQ=1`). The overlays keep the default deployment unchanged.

Core creates new indexing tables and runs `CREATE EXTENSION IF NOT EXISTS vector` when enabled. A database administrator may install the extension first if Core's database role lacks that privilege. Neo4j credentials need schema/index creation and read/write access; the graph database is selected with `HRAG_NEO4J_DATABASE` (default `neo4j`). Core alone connects to either database. Keep Bolt private; use `neo4j+s://` for verified TLS when connecting across untrusted networks.

In **Admin Settings > LLM Endpoints**, enable an **Embeddings** format on an OpenAI-compatible endpoint. Assign **HRAG embeddings**, **HRAG entity and relationship extraction**, and **HRAG graph planning**. These require realtime processing in v1. Chat's existing endpoint synthesizes and streams answers. Set `HRAG_EMBEDDING_DIMENSIONS` to the embedding model's output dimension (default 1536). Provider changes create a separate generation; do not silently replace the model behind an unchanged model identifier.

Core and worker currently pin the companion llm-bot evidence tasks, backported onto release 0.1.6, to an immutable source archive. This retains the existing generative sentiment API; adopting a later library release also requires reviewing its sentiment transport change. Core installs the transport-free library; workers install its `inference` extra. This avoids mixing Requests and Niquests transport packages in Core.

## Inputs and indexing

Only NewsItem **content** is sent for indexing. Extraction uses the first 20,000 Unicode characters (`HRAG_EXTRACTION_LIMIT`); one embedding uses the first 4,000 (`HRAG_EMBEDDING_LIMIT`). The limits are independent. Title, review, tags, and regrouping do not trigger inference. Content edits beyond the relevant cutoff reuse that pipeline's result. Empty content needs no inference. Panels identify truncated items.

The fixed v1 vocabulary preserves existing NER types and adds vulnerability, campaign, incident, mitigation, location, infrastructure, motivation and capability. Every entity/relation needs an exact source passage; relations retain affirmation, negation or uncertainty. Only validated CVE identifiers merge across articles in v1. Names remain separate, and aliases cannot establish multi-hop factual paths. Extraction exposes a deterministic compatible NER-tag projection; standalone NER remains available. HRAG indexing does not invoke a second NER task.

PostgreSQL stores generation configuration, fingerprints, leases, retries, extraction output, and vectors. Redis executes work; it is not the index ledger. Startup queues reconciliation, and cron repeats it every minute. Each pass scans up to 500 items per generation and queues up to 50 jobs. A lost queued/running job becomes eligible after its 15-minute durable lease. Failed jobs use bounded exponential backoff up to one hour. Repeated callbacks are idempotent; outdated fingerprints and lease tokens are rejected. Missing Neo4j projections rebuild from saved extraction output without another inference call. Deletions cascade in PostgreSQL; reconciliation prunes graph assertions and unused entities.

Administrators can use the authenticated API:

- `GET /api/settings/hrag`: generations and work counts.
- `POST /api/settings/hrag` with `{"action":"backfill"}`: queue reconciliation now.
- `POST /api/settings/hrag` with `{"action":"activate","generation_id":"…"}`: activate a completed generation, after rechecking all current inputs.
- `POST /api/settings/hrag` with `{"action":"reprocess","generation_id":"…"}`: invalidate and rerun that generation. This incurs inference again.

The first generation of each pipeline becomes active during its initial backfill. New model, input-limit or schema configurations build alongside the active generation and require explicit activation. Old generations remain stored. Credentials can rotate without changing the generation; the model, format and destination are frozen. Use a new model identifier or schema version when replacing model weights in place.

## Retrieval and permissions

An LLM returns a constrained plan. Core selects fixed parameterized Cypher; model-generated SQL/Cypher is never executed. Default limits are three relationships, 50 graph evidence rows and 12 vector matches (`HRAG_GRAPH_LIMIT` and `HRAG_VECTOR_LIMIT`). Multi-hop paths use affirmed assertions only. Both branches apply the planned Assess filters. If planning itself fails, vector matching uses no inferred filters and the partial-retrieval notice makes that limitation visible.

Current source ACLs, story and NewsItem TLP, active generations and content fingerprints determine eligible assertions before traversal output, ranking and limits. Every supporting assertion in a path must pass. Core rechecks before synthesis and display, and resolves current story membership. Saved messages retain references, not copied passages. Answers whose evidence or inherited conversation evidence becomes inaccessible are withheld on reload and from later provider context.

Vector retrieval currently uses exact cosine ranking over authorized items. This preserves correct filtered top-k results and supports mixed stored dimensions across separate generations; a future ANN optimization must preserve that authorization behavior. Corpus scans and authorized-key lists favor straightforward correctness in v1; measure larger deployments before assuming benchmark timings apply to application queries.

One retrieval failure yields a partial answer and a notice. Two failures leave the turn unsaved. Successful empty retrieval reports insufficient evidence. Counts are explicitly limited to indexed, accessible, retrieved evidence and cannot be treated as complete corpus counts.

## Backup and recovery

Back up PostgreSQL with its normal procedures, including HRAG tables, settings and pgvector. Neo4j is a rebuildable projection. After restoring PostgreSQL into a compatible pgvector-enabled database, an empty Neo4j instance can be rebuilt by reconciliation; embedding vectors remain in PostgreSQL. For a Neo4j Community dump, stop the database/DBMS as required by the installed Neo4j version; do not assume Enterprise online backup is available. Validate restores in an isolated environment before relying on them.

Disabling `HRAG_ENABLED` stops indexing and new HRAG turns while preserving PostgreSQL data and Chat history. Existing history still rechecks evidence permissions. The scoped integration/browser checks use disposable Neo4j and pgvector services and a scripted provider; they establish workflow correctness, not the factual quality of a chosen extraction or embedding model.

## Model quality evaluation

The selected private corpus remains at `taranis_data/hrag/sample.json` (120 items from 33 sources). Once extraction and embedding endpoints are selected, run `dev/evaluate_hrag.py` in the worker environment with `--sample`, `--endpoints`, `--dimensions`, and `--output`. The endpoint file contains `extraction` and `embedding` endpoint objects, including credentials if needed; keep it outside Git. Write output under ignored `taranis_data/hrag/`. Metrics count schema/passage-valid outputs, truncation, entities and relationships. The private annotation JSONL keeps source references, existing NER tags and review fields for assessing correctness and missed assertions. Existing tags and automatically valid quotes do not establish semantic correctness.

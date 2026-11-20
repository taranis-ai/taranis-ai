# HRAG implementation: a guided source walkthrough

This guide describes the HRAG implementation on `feature/hrag`, introduced after `711a09d66`. It explains the checked-in code, rather than a generic graph-RAG architecture. The editable [draw.io diagram](../diagrams/hrag-implementation.drawio) accompanies it. Open the file in draw.io / diagrams.net and use the five page tabs. Node IDs below match the diagram.

For deployment and administrator instructions, see [Hybrid retrieval in Chat](hrag.md). This guide does not change application behavior.

## 1. Start with the component map

**Diagram page 1, O1–O9.** HRAG adds a retrieval mode to the existing analyst Chat. It has two flows:

1. **Background indexing:** periodically discover NewsItem content, extract source-backed entities/relations, create embeddings, and persist both results.
2. **An analyst turn:** plan a graph search, retrieve authorized graph and semantic evidence, then use the existing Chat provider to synthesize an answer with citations.

Core owns database access, permissions, indexing state, retrieval, and chat orchestration. The worker executes indexing inference and calls Core to claim and submit work. Redis/RQ transports jobs; PostgreSQL is the durable ledger. Neo4j is a rebuildable graph projection of extraction results saved in PostgreSQL.

| Responsibility | Main implementation |
| --- | --- |
| Backend-independent schemas, vocabulary, identities, fingerprints | [models/hrag.py](../../src/models/models/hrag.py) |
| Generation and work lifecycle | [service/hrag/indexing.py](../../src/core/core/service/hrag/indexing.py) |
| RQ execution and indexing inference | [worker/hrag.py](../../src/worker/worker/hrag.py) |
| Neo4j projection/traversal and pgvector SQL | [service/hrag/stores.py](../../src/core/core/service/hrag/stores.py) |
| Planning, live authorization, retrieval, evidence reconstruction | [service/hrag/retrieval.py](../../src/core/core/service/hrag/retrieval.py) |
| Turn lifecycle, synthesis, persistence, history protection | [service/chat.py](../../src/core/core/service/chat.py) |
| New ORM tables | [model/hrag.py](../../src/core/core/model/hrag.py) |
| Settings and worker HTTP boundaries | [api/settings.py](../../src/core/core/api/settings.py), [api/worker.py](../../src/core/core/api/worker.py) |
| User Chat HTTP boundary | [api/chat.py](../../src/core/core/api/chat.py) |
| Mode selection, rendering, evidence links | [chat_views.py](../../src/frontend/frontend/views/chat_views.py), [workspace.html](../../src/frontend/frontend/templates/chat/workspace.html) |

Paths shown in diagram blocks are repository-relative. In this guide, `models/hrag.py` means the shared Pydantic module; `model/hrag.py` means Core's SQLAlchemy module.

## 2. Understand the input and extraction contracts

**Diagram D1, D4; I3, I6.** Read shared `models/hrag.py` first.

Only `NewsItem.content` is indexed. `bounded_content()` takes a prefix by Python Unicode characters, rather than bytes or tokens. Defaults are 20,000 characters for extraction and 10,000 for embeddings; configuration can change each independently. Each pipeline has its own fingerprint:

```text
SHA256(generation_id + "\0" + bounded_content)
```

A title edit, review change, tag change or regrouping therefore does not require another model call. A content edit after character 10,000 but before character 20,000 invalidates extraction only. An edit beyond both cutoffs leaves both results reusable. Source title, story membership and permissions are resolved from current records later.

The LLM-facing `CompactExtractionResult` contains entity IDs, types and verbatim names, plus relationships with exact quotes and optional assertion polarity. Its `resolve()` method derives the existing `ExtractionResult` with `ExtractedEntity` and `ExtractedRelation` lists locally. Names and quotes must occur exactly in the bounded input; repeated occurrences resolve to the first match, and CVE identifiers require complete token matches. Dates, offsets, sentence IDs and separate entity quotations are not requested from the model. The fixed schema contains 20 entity types and 18 relationship kinds. `RELATION_ENDPOINTS` restricts which entity types may be the source and target of each kind. It also prevents an alias relation between different entity types.

Every entity and relation carries an `EvidenceSpan`:

```text
start / end = Unicode offsets into exactly the bounded extraction input
quote       = content[start:end]
```

`EvidenceSpan.valid_range()` checks offset/quote length consistency. `ExtractionResult.valid_graph()` checks unique entity IDs and relationship endpoints. `validate_content()` checks exact source substrings, requires a relation's date phrase to occur in its quote, and validates quoted CVE identifiers. Worker inference and Core submission both validate source evidence.

Relations explicitly retain `affirmed`, `negated` or `uncertain` assertions. An extracted relation is a claim made by its source; a valid quote establishes provenance, not that the model interpreted it correctly or that the source is true.

`ner_tags()` projects compatible entities into the existing NER vocabulary, mapping campaigns/incidents to EVENT and omitting ambiguous names and unsupported labels. It is a compatibility helper; HRAG indexing does not call a second NER task or automatically save a second set of standalone NER results.

## 3. Follow one item through background indexing

**Diagram page 2, I1–I9.** Read `indexing.py` alongside `worker/hrag.py`.

### 3.1 A startup or cron event triggers a scan

`queue_manager.py` maps `hrag_reconcile` to `worker.hrag.reconcile_index` and `hrag_index` to `worker.hrag.index_item`. With HRAG enabled, Core queues reconciliation at startup and publishes a minute cron specification. [cron_scheduler.py](../../src/worker/worker/cron_scheduler.py) includes the new task mapping. The cron process must actually be running for repeated scans.

`reconcile_index()` calls `POST /api/worker/hrag/reconcile`; `HragReconcile.post()` calls Core's `reconcile()`. Worker routes require the worker API key. Admin backfill uses the same queued reconciliation route through a separate administrator API.

There is no new synchronous extraction hook on every content edit. Periodic reconciliation discovers changes, while query-time fingerprint checks already exclude stale results.

### 3.2 Reconciliation resolves pipeline generations

`current_configuration()` resolves the `extraction` or `embedding` endpoint from Settings and requires realtime processing. It records endpoint ID, base URL, model, API format, input limit, schema version and dimensions. `reconcile()` hashes this configuration together with the pipeline name into a generation ID and serializes generation creation/scanning by locking the Settings row.

Extraction and embedding have independent generations. The first generation of a pipeline becomes active immediately while it backfills. A new configuration creates a separate inactive generation. Reconciliation services the currently selected configurations and active generations, allowing the existing index to continue while a replacement builds.

`generation_endpoint()` freezes the generation's model, URL and API format, but resolves current credentials from the named provider. Key rotation does not change the generation. Replacing model weights behind an unchanged model identifier is invisible to this fingerprinting scheme; use a new model identifier or schema version.

### 3.3 Scan source rows and update the durable ledger

For each selected/active generation, `reconcile()` scans up to 500 NewsItems ordered by ID using the generation cursor. It creates one `HragWork` per `(generation_id, news_item_id)` or resets changed work to pending with its new fingerprint. It updates truncation metadata and cycles the cursor back to the beginning when a scan finishes.

`scanned` records completion of a scan; activation still checks every current input rather than trusting that flag alone.

Reconciliation also compares saved extraction work against Neo4j document keys. Missing projections become pending while retaining saved extraction JSON, so the worker can replay them without inference.

### 3.4 Lease before enqueue; claim before inference

At most 50 eligible work rows per pipeline in each pass are marked queued with a 15-minute lease and committed before RQ enqueue. Work must be non-ready, outside its lease, and past `retry_after`. Failed enqueue releases the queued lease so a later pass can retry.

`index_item(work_id)` then calls `POST /api/worker/hrag/work/{work_id}`. `claim()` locks the row, rejects already-ready or currently-running work, verifies the current item and endpoint, and refreshes changed fingerprints. Blank/whitespace input becomes ready without inference and remains ineligible as retrieval evidence.

Otherwise, claim sets `running`, generates a fresh token, renews the 15-minute lease, increments attempts, and returns an `IndexJob`. The payload contains bounded content, pipeline, endpoint credentials, dimensions, fingerprint, token, and an optional cached result. This HTTP response has `Cache-Control: no-store`.

### 3.5 The worker performs one pipeline

`infer()` returns `cached_result` immediately when present. Otherwise:

- Extraction uses the companion library's shared `prepare_entity_relationship_extraction()` task with the fixed vocabulary, `CompactExtractionResult`, and a Taranis source validator. Taranis resolves exact spans, quarantines malformed relationships, and verifies valid candidates through Decisions before submission.
- Embedding uses llm-bot’s `EmbeddingClient` to build the `/embeddings` request and validate its result through `worker/embedding.py`. The worker HTTP transport retains pooling and credential handling. The request specifies the generation’s `dimensions`; the vector must be finite, nonzero and match that length.

The worker submits an `IndexSubmission` by PUT to the same work URL. It never writes PostgreSQL or Neo4j directly. On failure it logs details, attempts a `failed=True` callback, and raises a static job error.

### 3.6 Core accepts, projects and marks ready

`submit()` checks the lease token, submitted fingerprint and current source fingerprint under locks. Stale results return 409. Successful repeated callbacks are idempotent while their token/fingerprint still match.

For extraction, the worker first resolves the compact output into canonical evidence spans. Core validates passages again, stores extraction JSON in `hrag_work.result`, and commits it **before** calling `project_graph()`. This deliberate separation permits recovery after graph failure without paying for extraction again. Projection IDs are frozen before that commit so an old callback cannot relabel its result with a new fingerprint.

Core validates chunk offsets and dimensions against the frozen generation. `save_chunks()` replaces chunk rows atomically with work status; `hrag_work.result` stays empty.

Core then refreshes and locks the work again and checks token/content freshness before marking ready and clearing lease/retry fields. A content edit during projection cannot reactivate stale evidence. A stale graph projection can remain temporarily, but authorization excludes its key.

### 3.7 Failure and deletion recovery

The normal status path is:

```text
pending → queued → running → ready
                     |
                     +→ pending + retry_after   (reported failure)
```

A lost queued/running job becomes eligible after lease expiry. A failed callback sets bounded exponential backoff: `min(3600, 30 * 2 ** min(attempts, 7))` seconds. Thus the first normal claimed failure, with attempts=1, waits 60 seconds. There is no fixed attempt-count exhaustion in this ledger.

PostgreSQL deletes cascade from NewsItem/generation to work and from work to vector. Reconciliation prunes obsolete graph assertions/documents and unconnected entities. Pruning is best effort; permissions never rely on cleanup finishing.

## 4. Inspect exactly what is stored

**Diagram page 3, D1–D9.** Read Core `model/hrag.py` and `stores.py`.

| Store | Fields or structure | Why it exists |
| --- | --- | --- |
| `hrag_generation` | Configuration hash ID, pipeline, config JSON, active flag, scan cursor/scanned, created | Version the model/input/schema configuration separately per pipeline |
| `hrag_work` | Generation and NewsItem FKs; fingerprint, status, token, lease, retry, attempts, extraction result, truncation, updated | Durable per-item work and provenance ledger |
| `hrag_vector` | `work_id` PK/FK with cascade; `embedding vector NOT NULL` | Single-vector generations |
| `hrag_chunk_vector` | Composite work ID/chunk index key; source offsets, vector; cascade deletion | Multiple passages per item/generation |
| Neo4j `HDocument` | `key=work_id:fingerprint`, `work_id` | Identify the exact extraction revision being projected |
| Neo4j `HEntity` | Identity, casefolded name, entity type | Mention nodes and the limited shared CVE identity |
| Neo4j `H_MENTIONS` | Document → entity | Enable entity-only retrieval at zero hops |
| Neo4j `H_ASSERTION` | Source → target; key, work_id, kind, assertion, idx, date | Traverse source-backed relationships and resolve their original extraction record |
| `hrag_message` | Message FK/PK and metadata JSON | Evidence references, inherited dependencies, notices, filters and mode |
| Existing `chat_message` | User/assistant text and existing Chat metadata | Persist the actual conversation |

`db_manager.initial_database_setup()` imports the HRAG ORM model and creates metadata tables. `initialize_vectors()` runs only when enabled and using PostgreSQL, installs the vector extension if needed, and creates `hrag_vector` with raw SQL. The vector table is not an ORM model. Its dimension is not fixed in DDL, allowing separate generations with different dimensions; retrieval selects only the active authorized generation.

`project_graph()` creates unique constraints on entity ID and document key. Within a Neo4j write transaction it locks/merges the document, replaces that key's mentions/assertions, and writes entities/relations. Quotes stay in PostgreSQL extraction JSON. `idx` points back to the original relation; graph results are not trusted as the source of display passages.

### Why cross-document identity is deliberately limited

`entity_identity()` shares only syntactically valid, source-validated CVE names, normalized to uppercase. Other entities receive an identity scoped to the item and extraction revision. Two articles mentioning “APT29” do not automatically share an actor node. This prevents a name match from silently establishing a factual join.

For example, two source-backed edges may connect through the same CVE:

```text
article A: Alpha ──EXPLOITS──> CVE-2026-9999
article B: Beta  ──EXPLOITS──> CVE-2026-9999
```

The undirected traversal can find the Alpha–CVE–Beta path. It shows that the sources describe both groups exploiting that CVE; it does not establish an affiliation between Alpha and Beta. Both supporting articles must be accessible. Aliases cannot be used as multi-hop bridges.

## 5. Walk an analyst question through retrieval

**Diagram page 4, R1–R9.** Read `retrieval.py`, then the HRAG branch of `ChatService._create_turn()`.

### 5.1 Reuse Chat's request and turn controls

The frontend posts `mode=hrag` in the existing `ChatTurnRequest` contract in [models/chat.py](../../src/models/models/chat.py). Core's Chat API requires `ASSESS_ACCESS` and an available Chat provider; `retrieve()` separately checks `HRAG_ENABLED`. Conversation lookup enforces ownership.

`ChatService.create_turn()` acquires the existing Redis turn lease and establishes a 540-second shared deadline. The context includes current UTC time, analyst timezone, the latest ten saved messages, the user's visible filter catalog, accessible recent search results, and the latest question. HRAG indexing jobs are asynchronous; answering this question runs in Core during the Chat request.

### 5.2 Resolve Chat filters, then ask for a graph plan

Chat first resolves filters with its existing `search_stories` call and validates catalog/recent-result references and timezone values through the existing search helpers. `retrieve()` receives those filters explicitly. It builds a `GraphQueryGenerationRequest` from the question, fixed vocabulary and conversation text only, then calls `prepare_graph_query_generation()` through the deadline-aware `PlanningClient`.

`GraphPlan` constrains names, entity types, known relationship kinds and hops from 0 to 3. Names normalize to stripped casefolded strings. Assess filters are not part of this plan.

The model does not supply SQL or Cypher. `compile_graph()` chooses one of two fixed Cypher statements and binds plan values as parameters.

### 5.3 Authorize graph inputs before traversal limits

`iter_authorized_work()` combines current Story visibility/filter queries, NewsItem ACL, both Story and NewsItem TLP, an active generation, ready work, nonblank bounded content, and a fresh content fingerprint. Extraction work produces the allowed graph keys.

`graph_search()` binds those keys to fixed Cypher. A zero-hop plan searches document/entity mentions. A nonzero-hop plan traverses up to three relationships, in either direction, filters relationship kinds, and applies names/types to the starting entity.

Every relationship in a path must have an allowed key. Single-hop evidence can retain affirmed, negated or uncertain claims. Multi-hop paths require affirmed assertions and exclude `ALIAS_OF`. Relation descriptions retain the original edge direction even though traversal is undirected.

Graph results are bounded and ordered by path length and the first evidence key, rather than a learned relevance score. Retrieval creates `[G1]`, `[G2]`, etc. with path IDs, relation indices and all supporting keys. It avoids adding a path if its evidence would exceed the graph-row budget; the default/hard maximum is 50 evidence rows.

### 5.4 Embed the question and rank authorized vectors

After the graph attempt, the vector branch resolves the active embedding generation and uses llm-bot’s `EmbeddingClient` request/response handling through the deadline-aware `ProviderTransport` shared with Chat. It embeds `context["latest_message"]`, not an LLM-rewritten query or the entire conversation. It explicitly requests the active generation's configured `dimensions` and checks the returned dimensions.

It gathers authorized embedding work with the same Chat-resolved filters and verifies that the generation did not change during query embedding. `vector_search()` performs:

```sql
SELECT work_id
FROM hrag_vector
WHERE work_id = ANY(:ids)
ORDER BY embedding <=> CAST(:vector AS vector), work_id
LIMIT :limit
```

This is exact cosine-distance ranking over the allowed items. Filtering occurs before top-k, so hidden nearest neighbours cannot consume the result budget. Runtime settings default to 12 chunks and at most 3 per NewsItem, with each cap permitting up to 100. Per-item limits apply before the total limit. Generations freeze chunk size, overlap, enabled state and content limit. `hrag_chunk_vector` stores work ID, chunk index, source offsets and vector. References reconstruct exact passages from current source content. Single-vector generations use `hrag_vector`.

Graph and vector attempts run sequentially. Their results are appended to one `HragResult`; there is no reciprocal-rank fusion, shared numeric scoring or separate reranker.

### 5.5 Reconstruct source evidence and handle partial retrieval

`reauthorize()` reloads the user and current work and checks both the reference fingerprint and every `support_ids` fingerprint. `evidence_from_reference()` reconstructs `RetrievalEvidence` from the current item and durable extraction result:

- A relation reference resolves the exact original relation quote, names, assertion and optional date.
- A zero-hop graph reference combines distinct entity evidence quotes.
- A vector reference returns bounded content.

All branches include current story ID/title and truncation metadata. `reference_metadata()` strips display passages down to references for persistence.

| Situation | Turn behavior |
| --- | --- |
| Graph fails, vectors succeed | Use vector evidence and show a partial-retrieval notice |
| Planning fails, vectors succeed | Use vector evidence with the Chat-resolved filters and report the graph-planning failure |
| Vectors fail, graph succeeds | Use graph evidence and show a partial-retrieval notice |
| Both branches fail | Raise a Chat provider error; do not save the turn |
| Retrieval succeeds but produces no authorized evidence | Save the static “Insufficient indexed evidence…” answer |

Every result also carries a notice that evidence covers only currently accessible indexed content. Retrieved evidence cannot support complete corpus counts.

### 5.6 Synthesize and save through the existing Chat flow

The HRAG branch reauthorizes references immediately before synthesis and rebuilds checked conversation history. `hrag/answering.py` maps authorized evidence into the library's `HragRequest` and executes `prepare_hrag()` through the existing Chat provider. Only the decoded JSON answer field streams through `ChatTurnStream`; full answer/citation validation precedes persistence. Without evidence, it uses the static insufficient-evidence answer.

Core checks current evidence again after generation and checks inherited history dependencies before persistence. It saves user and assistant messages together, with `HragMessage` metadata in the same final transaction. A failed provider response or detected evidence change prevents saving that message pair.

The frontend's `_message_views()` adds current Assess links using `story_id`. `workspace.html` renders escaped answer text and expandable Graph evidence / Similar passages panels, with citations, quotes, relation polarity and truncation notices. The diagram names the HTML file explicitly because the selector and panels are implemented there rather than in Python.

## 6. Follow history and permission changes

**Diagram S1–S3.** Inspect `_conversation_detail()`, `_history_payload()` and `_history_dependencies()` in `service/chat.py`.

Saved HRAG metadata contains references rather than copied evidence passages. The assistant answer text itself remains stored in `chat_message`; withholding changes what is returned, not the original stored text.

On reload, `_conversation_detail()` calls `display_result()` to reauthorize and reconstruct evidence. If any saved reference or inherited dependency is unavailable, it replaces the returned answer with a static message explaining that the evidence changed or is inaccessible. `_history_payload()` uses this checked detail, so later provider context receives the placeholder instead of the withheld answer.

`_history_dependencies()` gathers accessible references/dependencies from the latest context window. A later ordinary Chat turn can depend on an earlier HRAG answer, so it also persists these dependency references. Revoking the underlying evidence therefore affects derived answers even when their mode was Chat.

This also explains why edits, deletion or switching active generations can make an older answer unavailable. Live fingerprint and active-generation checks take precedence over the saved answer. Regrouping alone can preserve evidence while changing its Assess destination because current story membership is reconstructed.

A multi-hop citation depends on its whole path: losing an intermediate supporting assertion invalidates the citation even if its own quoted item remains accessible.

## 7. Configuration and operational entry points

**Diagram O3, O9; S4–S6.** Read [config.py](../../src/core/core/config.py), shared [models/llm.py](../../src/models/models/llm.py), Settings and the Compose overlays.

| Setting or assignment | Role |
| --- | --- |
| `CHAT_ENABLED` | Existing Chat availability; required for HRAG chat turns |
| `HRAG_ENABLED` | Opt-in indexing/retrieval; frontend also uses it to show the mode selector |
| `HRAG_NEO4J_URI/USER/PASSWORD/DATABASE` | Core's graph connection; default database `neo4j` |
| `HRAG_EXTRACTION_LIMIT` | Default 20,000 Unicode characters |
| `HRAG_EMBEDDING_LIMIT` | Default 10,000 Unicode characters |
| `HRAG_EMBEDDING_DIMENSIONS` | Default 1536; explicitly requested and verified; must be supported by the model |
| `HRAG_GRAPH_LIMIT` | Default 50, maximum 50 graph evidence rows |
| `HRAG_VECTOR_LIMIT` | Default 12, maximum 100 vector matches |
| `llm_extraction_endpoint` | Realtime entity/relation extraction |
| `llm_embedding_endpoint` | Embeddings-capable provider for indexing and questions |
| `llm_graph_planning_endpoint` | Realtime constrained graph planning |
| Existing `llm_chat_endpoint` | Final answer synthesis and streaming |

Endpoint resolution can inherit the shared default when no explicit assignment is set, subject to capability checks. Shared LLM contracts and Core Settings reject incompatible assignments; extraction, relationship verification, embedding and graph planning require realtime processing. Worker [endpoint_health.py](../../src/worker/worker/endpoint_health.py) adds embedding probes that request and verify the configured HRAG dimension when enabled, and [llm.py](../../src/worker/worker/llm.py) handles the added generative feature names.

Core installs the transport-free companion library and workers its inference extra. The dependency is pinned to `taranis-llm-bot==0.1.8` from PyPI; the embedding client, prepared extraction/planning tasks and final structured HRAG task live in that dependency. See the component `pyproject.toml` files for the dependency and extras.

`GET /api/settings/hrag` requires `ADMIN_OPERATIONS` and reports enabled state, generations and grouped work counts. Optional repeated `news_item_id` query parameters restrict counts (up to 500 IDs). POST actions use `IndexAction`:

| Action | Implementation and effect |
| --- | --- |
| `backfill` or `reconcile` | Queue reconciliation; success returns 202 |
| `activate` with `generation_id` | Require scanned and every current item ready with matching fingerprint; atomically switch this pipeline's active generation |
| `reprocess` with `generation_id` | Clear results, leases, tokens and retry state; reset scan; rerun inference |

Old generations remain stored. The first generation is usable before its initial backfill completes, so early answers can have incomplete coverage. Activation of replacements is stricter. Graph planning is a per-turn task, not a third persisted indexing pipeline.

The Compose overlays add Neo4j Community and replace the database image with pgvector-enabled PostgreSQL 18. The host-development overlay exposes graph ports on loopback. Neither overlay alone enables Chat or starts an otherwise-disabled cron process. Use the existing deployment guide for setup details and database-version compatibility.

Use a Neo4j database dedicated to this installation: `prune_graph()` cleans all HRAG-labelled records absent from the current installation's valid key set. Back up PostgreSQL, including vectors and extraction output. Neo4j can be reconstructed from those results; Redis is execution state. Disabling HRAG retains stored data, and saved history continues to recheck evidence.

## 8. Existing checks to read for concrete examples

These are source-reading entry points, not a claim that tests were run while writing this documentation.

| Existing file | Useful behavior to inspect |
| --- | --- |
| [test_hrag_contracts.py](../../src/core/tests/unit/test_hrag_contracts.py) | Exact quotes, endpoint types, CVE identity, NER projection, independent cutoffs |
| [test_hrag_indexing.py](../../src/core/tests/unit/test_hrag_indexing.py) | Claim/replay, stale callbacks, cutoff edits, expired leases, retries, new generations and cascade deletion |
| [test_hrag_stores.py](../../src/core/tests/integration/test_hrag_stores.py) | Real pgvector and Neo4j: authorized top-k, shared CVE paths, negation exclusion, projection replay, stale keys and deletion |
| [test_hrag.py](../../src/worker/tests/unit/test_hrag.py) | Worker claim, extraction submission, cached retry, rejection of invalid vectors |
| [test_chat_client.py](../../src/core/tests/unit/test_chat_client.py) | HRAG synthesis, evidence history and Chat integration alongside the existing transport checks |
| [test_rbac.py](../../src/core/tests/application/mixed_flows/security/test_rbac.py) | Evidence visibility across source access changes |
| [test_chat_view.py](../../src/frontend/tests/unit/views/test_chat_view.py) | Mode submission and evidence link rendering |
| [test_e2e_workflow.py](../../src/frontend/tests/playwright/test_e2e_workflow.py) | Browser HRAG workflow with scripted provider and disposable services |

The branch tip removed `dev/evaluate_hrag.py`; it is not an available implementation entry point even though the older operational HRAG page still mentions it. Scripted-provider workflow checks establish mechanics, not extraction quality for a real model.

## 9. Suggested reading session

1. Open diagram page 1 and locate the Core/worker/database boundaries.
2. Read shared `models/hrag.py`, then page 3 to connect contracts to persisted records.
3. Follow page 2 with `reconcile() → claim() → infer() → submit()` open side by side.
4. Read `project_graph()`, `compile_graph()` and `vector_search()` in `stores.py`.
5. Follow page 4 with `retrieve()` and the `mode == "hrag"` branch of `_create_turn()`.
6. Finish with page 5 and the three Chat history helpers. Trace a source becoming inaccessible and see which checks withhold evidence and dependent answers.

For a concrete debugging exercise, pick a NewsItem ID and correlate its `hrag_work` rows with their generation configurations. The extraction work's `id:fingerprint` locates its Neo4j projection; the embedding work's ID locates its vector. A saved citation points back through work ID/fingerprint/relation index to that exact extraction revision, while its displayed title and story link come from the current source record.

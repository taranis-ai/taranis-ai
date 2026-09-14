# Fuzzy Deduplication and Collection Updates

## When To Load

News-item fingerprints, collection identity, URL updates, fuzzy grouping, revisions, or the fuzzy-hash migration. Also read [use cases](../fuzzy-hash-use-cases.md).

## Contracts

- `CollectionService` owns worker news-item ingestion. Identity is the sanitized URL within the source; missing URLs use exact source/title/body identity. Preserve manual/import/MISP/RT paths. Collection hashes use source-scoped identity; explicit title/URL checks use `get_by_payload_identity` so they also recognize collected items.
- Same-URL changes update source-owned title/body/author/language, preserving item ID, original collection date, analyst fields, and membership. Empty replacements are rejected. Story titles are not rewritten. Core records before/after story snapshots; the shared revision diff compares existing item fields.
- Core hashes sanitized content with fuzzbite after NFC/whitespace normalization. Bodies below 256 UTF-8 bytes have no fingerprint but still support URL updates. Exclude fingerprints from serialization/imports.
- Fallback matches compare same-source items collected in inclusive UTC `[now - 30 days, now]`. Select the strongest score across cursor partitions of 500. `COLLECTION_GROUP_THRESHOLD` defaults to 85 (1–100). Ties across different stories do not auto-group. Distinct URLs are retained even at score 100; there is no high-score discard band.
- Hold the source row lock across lookup/mutation and lock existing stories for revisions/membership changes. Commit per item. SQLite does not enforce row locks. Never merge/delete historical duplicates; the newest legacy item with the URL is selected.
- Reject incoming items only when their `published` value is strictly older than the stored value. Equal dates still undergo content comparison. Accepted newer dates update `published`, including unchanged content, without changing `updated` or creating revisions solely for a date change. Missing publication dates use the existing current-UTC fallback. Equal publication dates cannot order different source versions; no extra per-item observation timestamp is stored.
- Changes mark stories unread and set `collection_updated_at`; relative date windows include that activity, while explicit `timefrom` remains publication-based. Post-collection bots receive affected IDs to bypass already-processed filters. MISP refresh follows domain commits.
- Results contain counts and affected IDs. Preserve `All news items were skipped` for unchanged/stale-only runs, which collectors translate to `NOT_MODIFIED`. Invalid payloads are errors, not skipped duplicates.
- The unmerged PostgreSQL migration adds the story collection-activity timestamp and fingerprints and backfills fingerprints within the 30-day window. No content or old timestamps are rewritten. Already-applied development copies need reapplication/recreation after this branch's migration edits.
- RSS summaries and shared boilerplate can cause false grouping. Detection only covers retrieved articles; independent revisits are not implemented. See [Collector HTTP State](collector-http-state.md) for resource-scoped validators.

## Entry Points and Coverage

Core: `core/service/collection.py`, `core/model/news_item.py`, `core/model/story.py`, `core/api/worker.py`, `core/managers/queue_manager.py`, and `migrations/20260911_01_f8H2q-add-news-item-fuzzy-hash.py` under `src/core`.

Shared diffs: `src/models/models/revision_diff.py`. Worker: `base_collector.py`, `base_web_collector.py`, `collector_tasks.py`, and `core_api.py`.

`CollectionService.ingest_item` handles source locking and identity dispatch; `_update_item` and `_create_item` handle their respective decisions, with `_record_change` sharing status/revision work. Transaction commits remain owned by `ingest`.

Core worker-pipeline tests cover identity, history, stale retries, scope, threshold boundaries, and invalid batches. Worker collector tests cover validator scope and update-only post-collection dispatch. Frontend `test_collected_article_updates_and_grouping` verifies the displayed diff and two retained grouped URLs. Follow the normal full feature signoff workflow.

# Fuzzy Deduplication

## When To Load

News-item fingerprints, collection deduplication, or the fuzzy-hash migration.

## Contracts

- Core hashes sanitized content with `ppdeep` after NFC and whitespace normalization. Bodies under 256 UTF-8 bytes remain NULL. Recompute on content edits; exclude fingerprints from serialization and untrusted import fields.
- Worker news-item ingestion always checks fuzzy similarity after the globally unique exact title/URL hash. Compare the same source's items collected in the inclusive UTC interval `[now - 30 days, now]`; skip at score 90 or higher.
- The `collection=True` argument identifies the ingestion boundary. Manual/missing sources, explicit creation, JSON imports, MISP/RT synchronization, and conflict resolution retain their existing identity rules.
- Hold the PostgreSQL source-row lock through check and insertion; release it after each skipped item before processing another source. SQLite does not enforce row locks.
- Preserve `All news items were skipped`, which collectors translate to `NOT_MODIFIED`. Never merge or delete existing items.
- The PostgreSQL migration adds the column/index and fills missing fingerprints only within the same UTC 30-day window, using a bounded cursor in its transaction. It preserves content and timestamps. There is no separate CLI operation.
- RSS can supply summaries/descriptions rather than full articles; shared boilerplate can produce false matches. Concatenating titles into the body hash does not reliably distinguish different headlines. Content-only matching deliberately tolerates rewritten headlines.

## Entry Points

`src/core/core/model/news_item.py`, `src/core/core/model/story.py`, `src/core/core/api/worker.py`, and `src/core/migrations/20260911_01_f8H2q-add-news-item-fuzzy-hash.py`.

Minimal collection/scope tests live in `src/core/tests/application/worker_pipeline/test_worker_api.py`. Existing collector tests cover `NOT_MODIFIED` handling. See [OSINT sources](../osint-sources.md#fuzzy-deduplication) for behavior and limitations.

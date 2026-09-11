# Fuzzy Deduplication

## When To Load

News-item fingerprints, fuzzy duplicate detection, collection ingestion, or fingerprint backfill.

## Contracts

- Core computes internal `fuzzy_hash` from sanitized content using `ppdeep` CTPH after NFC and whitespace normalization. Bodies under 256 UTF-8 bytes remain NULL. Recompute on content edits; exclude fingerprints from serialization and untrusted import fields.
- Exact title/URL hashing remains first and globally unique. Opt-in fuzzy rejection is passed explicitly from the worker news-item endpoint via `collection=True`. Do not enable it in shared constructors, manual/JSON creation, MISP/RT synchronization, or conflict resolution.
- Candidates share the real OSINT source ID and have `collected` in the inclusive UTC interval `[now - lookback, now]`. Manual/missing sources bypass fuzzy comparison. Defaults are disabled, 30 days, score 90. Lookback is 1–365; score is 1–100. Scores do not prove semantic equivalence, including at 100.
- PostgreSQL locks the source row through check and insert. Release locks after each skipped item too, before processing another source, to avoid retaining locks across mixed-source batches. SQLite does not enforce row locks.
- Preserve the worker's skipped-item result, especially `All news items were skipped`, which becomes collector `NOT_MODIFIED`. Existing items/stories are never deleted or merged.
- The additive PostgreSQL migration adds the column/index only. CLI backfill locks and commits bounded batches, processes NULL fingerprints within a UTC window, and explicitly preserves `updated`. Reruns skip filled fingerprints and revisit short bodies. Do not run a corpus backfill during server startup.

## Entry Points and Coverage

`src/core/core/model/news_item.py`, `src/core/core/model/story.py`, `src/core/core/api/worker.py`, `src/core/core/config.py`, and `src/core/core/cli.py`.

Behavior/backfill coverage: `src/core/tests/application/worker_pipeline/test_fuzzy_ingestion.py`. Real PostgreSQL race and released-schema migration coverage: `test_fuzzy_postgres.py` in the same directory; set `TARANIS_TEST_POSTGRES_URI` to an isolated test database. The fixture creates and drops a unique schema. Config validation: `src/core/tests/test_settings.py`. Existing collector tests own `NOT_MODIFIED` handling.

Operator instructions and rollback limitations: [OSINT sources](../osint-sources.md#fuzzy-deduplication).

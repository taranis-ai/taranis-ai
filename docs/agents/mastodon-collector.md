# Mastodon Collector

## When To Load

`MASTODON_COLLECTOR`, hashtag/home/account timelines, Mastodon.py, or cursor pagination.

## Contracts

- Scheduled polling, not streaming. Hashtags can be anonymous; home/account collection needs a masked read-only token. Token-bearing sources require HTTPS, enforced by shared validation and again before worker client creation. Tokenless HTTP is for development instances.
- Anonymous authentication rejection asks admins to configure a token; an invalid configured token is a distinct failure. Log static API failure messages because upstream exceptions may contain secrets.
- Default `COLLECTION_MODE=complete` uses `min_id` to collect all statuses since the cursor with no per-run limit. `latest` uses `since_id` for the newest 40-status page and a `min_id` probe to warn about skipped middle statuses. RSS entry limits do not apply.
- Both modes bootstrap from the newest page. Preview always fetches that page, ignores mode/cursor, and never persists progress.
- Cursor identity includes instance, timeline, and normalized hashtag/resolved account ID, but not collection mode. Identity changes reset progress; switching latest to complete cannot recover already skipped statuses.
- Advance only after successful publication (duplicate-only publication counts). Every subsequent result, including failures, carries the new or previous cursor. It lives in the latest task result and can disappear with history cleanup/deletion/inactivity; then bootstrap and rely on core deduplication.
- Keep replies/boosts. Boosts map to the original post URL for deduplication. Treat status IDs as opaque strings and paginate in API response order; do not use write-scoped Mastodon markers that change other clients' read position.
- Complete mode after long downtime can hit rate/resource limits.

## Entry Points and Coverage

`src/worker/worker/collectors/mastodon_collector.py`, `src/models/models/worker_parameters.py`, `src/core/core/model/osint_source.py`; setup: `docs/mastodon.md`.

Tests: `src/worker/tests/collectors/test_mastodon_collector.py`, `src/worker/tests/collectors/test_collector_tasks.py`, `src/core/tests/unit/test_worker_parameter_registry.py`, `src/core/tests/application/worker_pipeline/test_worker_api.py`.

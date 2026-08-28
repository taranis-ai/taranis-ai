# Mastodon Collector

## When To Load

Mastodon collector, hashtag timeline, home timeline, public account collection, Mastodon.py, Mastodon cursor, or `MASTODON_COLLECTOR`.

## Expected Behavior

Mastodon collection runs as scheduled polling rather than a long-lived stream. Hashtags may use public API access; home and account modes require a masked read-only access token. Each run processes at most the global `collector_max_entries` value, default 42.

When an instance rejects an anonymous hashtag request with an authentication-related response, collection fails with a static message telling the administrator to configure an access token. Invalid configured tokens remain a separate authentication failure.

New sources bootstrap from the newest statuses. Later runs move forward from a cursor retained in the latest collector task result without using or changing Mastodon markers. A failed API request or publish never advances progress. A preview ignores the cursor and never persists progress.

The cursor is intentionally best-effort state. Task-history cleanup, manual task deletion, or prolonged source inactivity can remove it; the next collection then bootstraps from the newest statuses and relies on core deduplication for replayed items.

Boosts become news items for the original post and deduplicate through its URL. Replies and boosts visible in the selected timeline are retained.

## Code Paths

- Worker API collection and mapping: `src/worker/worker/collectors/mastodon_collector.py`
- Parameter contract: `src/models/models/worker_parameters.py`
- Cursor worker payload: `src/core/core/model/osint_source.py`
- User setup: `docs/mastodon.md`

## Data Flow

Core expands validated source parameters and returns the global entry limit plus any valid cursor from the latest collector task result to the worker. The worker resolves the configured timeline, bootstraps backward or paginates forward with Mastodon.py, publishes mapped news items, and returns the new cursor in the next task result.

The timeline identity includes the instance, mode, and normalized hashtag or resolved account ID. A changed identity ignores the old cursor and establishes a new one only after successful publication.

## Testing

- Worker behavior: `src/worker/tests/collectors/test_mastodon_collector.py`, `test_collector_tasks.py`
- Parameter validation: `src/core/tests/unit/test_worker_parameter_registry.py`
- Cursor delivery and malformed-state rejection: `src/core/tests/application/worker_pipeline/test_worker_api.py`
- Settings: core admin settings tests

## Pitfalls

Do not use Mastodon markers: updating them requires write scope and changes the user's read position in other clients. Do not advance the cursor before core publication succeeds; duplicate-only publication is the exception because the statuses already exist. Every collector task result after initial progress must carry either the advanced or previous cursor so a failure does not reset progress. Treat Mastodon status IDs as opaque strings and use the API's response order for pagination. Use the original post URL for news-item deduplication. Keep exception-derived API text in server logs and return only curated task messages.

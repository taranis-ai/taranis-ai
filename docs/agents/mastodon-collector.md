# Mastodon Collector

## When To Load

Mastodon collector, hashtag timeline, home timeline, public account collection, Mastodon.py, Mastodon cursor, or `MASTODON_COLLECTOR`.

## Expected Behavior

Mastodon collection runs as scheduled polling rather than a long-lived stream. Hashtags may use public API access; home and account timelines require a masked read-only access token. Mastodon collection does not use the RSS entry limit. `COLLECTION_MODE=complete` is the default and collects every status since the cursor without a per-run limit. `COLLECTION_MODE=latest` imports only the newest 40-status page and warns when it skips older statuses.

Any Mastodon source with an access token must use an HTTPS instance origin. The shared parameter contract enforces the rule for enabled source creation, update, and import, and the worker rejects an insecure token-bearing payload before constructing the Mastodon client. Tokenless hashtag collection may use HTTP for development-only instances.

When an instance rejects an anonymous hashtag request with an authentication-related response, collection fails with a static message telling the administrator to configure an access token. Invalid configured tokens remain a separate authentication failure.

New sources bootstrap from the newest API page in either collection mode. Complete runs paginate through all statuses immediately newer than a cursor retained in the latest collector task result. Latest runs fetch the newest page after the cursor, then probe the oldest immediately newer status to determine whether any middle statuses were skipped. A failed API request or publish never advances progress. A preview ignores the cursor and collection mode, shows the newest API page, and never persists progress.

The cursor is intentionally best-effort state. Task-history cleanup, manual task deletion, or prolonged source inactivity can remove it; the next collection then bootstraps from the newest statuses and relies on core deduplication for replayed items.

Boosts become news items for the original post and deduplicate through its URL. Replies and boosts visible in the selected timeline are retained.

## Code Paths

- Worker API collection and mapping: `src/worker/worker/collectors/mastodon_collector.py`
- Parameter contract: `src/models/models/worker_parameters.py`
- Cursor worker payload: `src/core/core/model/osint_source.py`
- User setup: `docs/mastodon.md`

## Data Flow

Core expands validated source parameters, including the collection-mode default, and returns any valid cursor from the latest collector task result to the worker. The worker resolves the configured timeline, applies the selected cursor strategy, publishes mapped news items, and returns the new cursor in the next task result.

The timeline identity includes the instance, timeline selection, and normalized hashtag or resolved account ID. A changed identity ignores the old cursor and establishes a new one only after successful publication. Collection mode is not part of that identity, so switching modes continues from the existing cursor.

## Testing

- Worker behavior: `src/worker/tests/collectors/test_mastodon_collector.py`, `test_collector_tasks.py`
- Parameter validation: `src/core/tests/unit/test_worker_parameter_registry.py`
- Cursor delivery and malformed-state rejection: `src/core/tests/application/worker_pipeline/test_worker_api.py`

## Pitfalls

Do not use Mastodon markers: updating them requires write scope and changes the user's read position in other clients. Complete mode uses `min_id`; latest mode deliberately uses `since_id` and must warn when its `min_id` probe proves that middle statuses were skipped. Switching from latest to complete cannot recover statuses behind the advanced latest cursor. Do not advance the cursor before core publication succeeds; duplicate-only publication is the exception because the statuses already exist. Every collector task result after initial progress must carry either the advanced or previous cursor so a failure does not reset progress. Complete mode after extended downtime can process many pages and hit rate or resource limits. Treat Mastodon status IDs as opaque strings and use the API's response order for pagination. Use the original post URL for news-item deduplication. Log only static Mastodon API and response-failure messages because upstream exception text may contain secrets; return only curated task messages.

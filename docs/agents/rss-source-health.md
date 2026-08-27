# RSS Source Health

## When To Load

RSS collectors, Atom feeds, feedparser validation, empty feeds, OSINT source state, collector task results, or source error messages.

## Expected Behavior

An RSS source fails immediately when feedparser cannot identify the response as RSS or Atom. A conditional 304 after that failure keeps the source failed because the unchanged response cannot prove that the feed became valid. A parseable feed with no entries is `NOT_MODIFIED` with the `rss_feed_empty` reason and a message explaining that the feed is valid but empty.

Each collection processes at most the global `rss_collector_max_entries` value from Admin Settings. The default is 42 and the setting must be a positive integer. The same limit applies to normal feeds and digest splitting.

Each state includes a user-facing message. Empty-feed results persist the current HTTP validators but do not count collection attempts or become failures.

## Code Paths

- Feed detection and item collection: `src/worker/worker/collectors/rss_collector.py`
- Global setting and worker source payload: `src/core/core/model/settings.py`, `src/core/core/model/osint_source.py`
- Admin form: `src/frontend/frontend/templates/settings/settings.html`
- Task state transitions and persisted messages: `src/worker/worker/collectors/collector_tasks.py`
- Source status lookup: `src/core/core/model/osint_source.py`
- Admin status badge and tooltip: `src/frontend/frontend/templates/macros/worker.html`

## Data Flow

Core includes the configured RSS entry limit and latest persisted collector task in the worker's OSINT source payload. The RSS collector rejects responses without a detected feed version and reports parseable feeds that produce no items separately. The collector task records an empty feed as `NOT_MODIFIED` with the `rss_feed_empty` reason. A later 304 preserves that reason and message so the user continues to see that the unchanged feed is empty. A 304 also preserves a preceding failure instead of marking it successful.

## Testing

Run `cd src/worker && uv run pytest tests/collectors/test_collector.py tests/collectors/test_collector_tasks.py` for focused coverage. For setting changes, also run the core admin/worker API tests and verify persistence from the Admin Settings page.

## Pitfalls

Do not reject a feed solely because feedparser sets `bozo`; malformed feeds can still be identifiable and usable. Empty means the parsed feed has no entries, not that filters or digest processing produced no publishable items. Do not add an empty-feed retry counter: repeated emptiness cannot distinguish a dormant valid feed from a broken one.

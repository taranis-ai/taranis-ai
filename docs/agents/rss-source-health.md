# RSS Source Health

## When To Load

RSS collectors, Atom feeds, feedparser validation, empty feeds, OSINT source state, collector task results, or source error messages.

## Expected Behavior

An RSS source fails immediately when feedparser cannot identify the response as RSS or Atom. A conditional 304 after that failure keeps the source failed because the unchanged response cannot prove that the feed became valid. A newly configured, parseable feed that produces no news items remains `PENDING` for its first two consecutive collection attempts and changes to `FAILURE` on the third. If the source has already completed successfully, a later empty feed is `NOT_MODIFIED` instead of restarting the pending sequence.

Each state includes a user-facing message. Pending and terminal empty-feed results use the `rss_feed_empty` reason and persist the current attempt plus the failure threshold in result data.

## Code Paths

- Feed detection and item collection: `src/worker/worker/collectors/rss_collector.py`
- Task state transitions and persisted messages: `src/worker/worker/collectors/collector_tasks.py`
- Source status lookup: `src/core/core/model/osint_source.py`
- Admin status badge and tooltip: `src/frontend/frontend/templates/macros/worker.html`

## Data Flow

Core includes the latest persisted collector task in the worker's OSINT source payload. The RSS collector rejects responses without a detected feed version and reports parseable feeds that produce no items separately. The collector task reads the preceding `rss_feed_empty` result, increments its persisted attempt count, and writes `PENDING` or `FAILURE`. Empty-feed results persist the current HTTP validators. A successful collection resets the sequence naturally because its result no longer has the empty-feed reason; a 304 preserves a preceding unsuccessful result instead of marking it successful.

## Testing

Run `cd src/worker && uv run pytest tests/collectors/test_collector.py tests/collectors/test_collector_tasks.py` for focused coverage. Validate the source badge and message from the admin OSINT Sources page for user-facing changes.

## Pitfalls

Do not reject a feed solely because feedparser sets `bozo`; malformed feeds can still be identifiable and usable. Empty means the parsed feed has no entries, not that filters or digest processing produced no publishable items. Empty-feed attempts are stored in task result data rather than a source column, so scheduled and manual collections share the same source status flow without a migration. Do not count a later empty response as a new-source failure when the preceding source status has a successful run.

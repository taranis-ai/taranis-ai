# RSS Source Health

## When To Load

RSS/Atom detection, feedparser, empty feeds, source status, or RSS entry limits.

## Contracts

- Fail when feedparser cannot identify RSS/Atom; an HTML `rel="alternate"` RSS/Atom link supplies the first suggested feed URL. `bozo` alone does not make an identifiable feed unusable.
- A parseable feed with no entries is `NOT_MODIFIED` with `rss_feed_empty`, not a failure. This means no parsed entries, not zero items after filtering/digest processing. Do not add retry counters: repeated emptiness cannot distinguish dormant from broken feeds.
- Preserve validators and prior empty/failure state on 304 as defined in [Collector HTTP State](collector-http-state.md).
- `rss_collector_max_entries` is a global positive integer, default 42, applying to normal feeds and digest splitting. Admin Settings warns outside 20–100 but permits any positive value.
- Truncating feed entries reports `WARNING` with `rss_entry_limit` and "Only N entries were considered, in the order provided by the feed (starting at the top). X additional entries were skipped." Count skipped feed entries before filtering, deduplication, or digest expansion; preserve the existing feed order. Duplicate-only publication still warns when entries were truncated. Successful publication still runs post-collection bots.
- The warning is appended to the normal collection result, preserving publication or duplicate-only context.
- A primary-feed HTTP 304 retains a prior entry-limit warning for the same URL. A freshly parsed feed within the limit clears it, including duplicate-only publication. Raising the limit requires a fresh response (manual collection bypasses validators).
- Warnings update successful-execution timestamps and appear in My Tasks, while source badges/details and task rows display warning styling. Warning completion invalidates frontend content caches like success. Dashboard/history statistics count warnings separately and show warning styling; see [Scheduler Dashboard](scheduler-dashboard.md).

## Entry Points and Coverage

`src/worker/worker/collectors/rss_collector.py`, `src/worker/worker/collectors/collector_tasks.py`, `src/core/core/model/settings.py`, `src/core/core/model/osint_source.py`, `src/frontend/frontend/templates/macros/worker.html`.

Tests: `src/worker/tests/collectors/test_collector.py`, `src/worker/tests/collectors/test_collector_tasks.py`; setting changes also need core admin/worker API coverage and Admin Settings persistence verification.

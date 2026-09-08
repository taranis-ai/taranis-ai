# RSS Source Health

## When To Load

RSS/Atom detection, feedparser, empty feeds, source status, or RSS entry limits.

## Contracts

- Fail when feedparser cannot identify RSS/Atom; an HTML `rel="alternate"` RSS/Atom link supplies the first suggested feed URL. `bozo` alone does not make an identifiable feed unusable.
- A parseable feed with no entries is `NOT_MODIFIED` with `rss_feed_empty`, not a failure. This means no parsed entries, not zero items after filtering/digest processing. Do not add retry counters: repeated emptiness cannot distinguish dormant from broken feeds.
- Preserve validators and prior empty/failure state on 304 as defined in [Collector HTTP State](collector-http-state.md).
- `rss_collector_max_entries` is a global positive integer, default 42, applying to normal feeds and digest splitting. Admin Settings warns outside 20–100 but permits any positive value.

## Entry Points and Coverage

`src/worker/worker/collectors/rss_collector.py`, `src/worker/worker/collectors/collector_tasks.py`, `src/core/core/model/settings.py`, `src/core/core/model/osint_source.py`, `src/frontend/frontend/templates/macros/worker.html`.

Tests: `src/worker/tests/collectors/test_collector.py`, `src/worker/tests/collectors/test_collector_tasks.py`; setting changes also need core admin/worker API coverage and Admin Settings persistence verification.

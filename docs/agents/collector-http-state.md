# Collector HTTP State

## When To Load

RSS/Simple Web conditional requests, ETag/Last-Modified, 304 results, collector dates, or failure propagation.

## Contracts

- Scheduled collection replays stored validators only when the configured primary URL still matches. Manual runs bypass conditional headers. ETags (including weak tags) are opaque and apply only to the primary URL; its Last-Modified is replayed on all direct/browser GETs, including articles, digests, attachments, and icons.
- Only a primary-resource 200 replaces validators. A 304 preserves them and reports `NOT_MODIFIED`, except it must retain a preceding failure or the `rss_feed_empty` reason/message. Unchanged content cannot prove recovery.
- Validator state is source-keyed runtime data, independent of task retention, exposed as worker-only `http_validators` and returned in task results. Do not put it in editable parameters or derive it from task times.
- Fetch/parse/publish failures propagate to `collector_task`, persist FAILURE, and prevent post-collection bots. Cleanup must still run and must not return from `finally`.

## Date Fallbacks

RSS uses the first parseable nonblank entry date, linked article date, channel `lastBuildDate`, then feed HTTP Last-Modified. The channel fallback also covers feed-content/no-link entries. Digest items start at linked article date. Browser article fallback uses the main navigation response, never secondary responses to update primary validators.

Ignore invalid Last-Modified dates. Parsed offset-aware dates become naive UTC; timezone-less values are treated as UTC. Persist/replay HTTP validator strings unchanged. Normalize legacy aware `last_attempted` to UTC before GMT formatting.

## Entry Points and Coverage

Worker: `src/worker/worker/collectors/base_web_collector.py`, `rss_collector.py`, `simple_web_collector.py`, and `collector_tasks.py` in that directory. Core: `src/core/core/model/osint_source.py`, `src/core/core/service/task.py`.

Tests: `src/worker/tests/collectors/test_collector.py`, `src/worker/tests/collectors/test_collector_tasks.py`, `src/core/tests/application/worker_pipeline/test_worker_api.py`. Scheduled collector E2E accepts SUCCESS and NOT_MODIFIED terminal outcomes. See [RSS Source Health](rss-source-health.md) for feed validation.

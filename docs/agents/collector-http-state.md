# Collector HTTP State

## When To Load

RSS/Simple Web conditional requests, ETag/Last-Modified, 304 results, collector dates, or failure propagation.

## Contracts

- Scheduled collection replays stored validators only when the configured primary URL still matches. Manual runs bypass conditional headers. ETags (including weak tags) are opaque and apply only to the primary URL; its Last-Modified is replayed on all direct/browser GETs, including articles, digests, attachments, and icons.
- Only a primary-resource 200 replaces validators. A primary-resource 304 preserves them and reports `NOT_MODIFIED`, except it must retain a preceding failure, the `rss_feed_empty` reason/message, or an RSS entry-limit `WARNING` for the same URL. Unchanged content cannot prove recovery. `HTTPNotModifiedError` identifies the URL and whether it is the primary resource; duplicate-only publication and secondary-resource 304s do not retain prior source health.
- Validator state is source-keyed runtime data, independent of task retention, exposed as worker-only `http_validators` and returned in task results. Do not put it in editable parameters or derive it from task times.
- Fetch/parse/publish failures propagate to `collector_task`, persist FAILURE, and prevent post-collection bots. Cleanup must still run and must not return from `finally`.

## Network Failures

Direct HTTP connection failures and timeouts in `send_get_request` use a static message advising checks of worker-container DNS, network access, and `PROXY_SERVER`. This covers every collector using the helper, including RSS, Simple Web, and RT. Original exception details are logged server-side at ERROR level, with tracebacks at DEBUG level, and suppressed from the displayed error chain. Connection and timeout diagnostics remain HTTP request exceptions, preserving RT’s existing per-item error handling. This adds no retries and does not diagnose DNS or an unreachable endpoint as the definite cause of a read timeout. The shared HTTP request test covers connection and timeout diagnostics, exception-chain suppression, and logging at INFO configuration. The RT collection test also covers per-item network failure fallbacks and continued collection.

## Date Fallbacks

RSS uses the first parseable nonblank entry date, linked article date, channel `lastBuildDate`, then feed HTTP Last-Modified. The channel fallback also covers feed-content/no-link entries. Digest items start at linked article date. Browser article fallback uses the main navigation response, never secondary responses to update primary validators.

Ignore invalid Last-Modified dates. Parsed offset-aware dates become naive UTC; timezone-less values are treated as UTC. Persist/replay HTTP validator strings unchanged. Normalize legacy aware `last_attempted` to UTC before GMT formatting.

## Entry Points and Coverage

Worker: `src/worker/worker/collectors/base_web_collector.py`, `rss_collector.py`, `simple_web_collector.py`, and `collector_tasks.py` in that directory. Core: `src/core/core/model/osint_source.py`, `src/core/core/service/task.py`.

Tests: `src/worker/tests/collectors/test_collector.py`, `src/worker/tests/collectors/test_collector_tasks.py`, `src/core/tests/application/worker_pipeline/test_worker_api.py`. Scheduled collector E2E accepts SUCCESS and NOT_MODIFIED terminal outcomes. See [RSS Source Health](rss-source-health.md) for feed validation.

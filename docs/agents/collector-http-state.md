# Collector HTTP State

Load for: RSS/Simple Web conditional requests, ETag/Last-Modified, 304 results, collector dates, or failure propagation.

## Contracts

- Scheduled collection replays stored validators only when the configured primary URL still matches. Manual runs bypass conditional headers. ETags (including weak tags) are opaque. Stored ETag and Last-Modified validators apply only to the primary URL; never replay feed validators to linked articles, digests, attachments, icons, or a shared browser session.
- Only a primary-resource 200 replaces validators. A primary-resource 304 preserves them and reports `NOT_MODIFIED`, except it must retain a preceding failure, the `rss_feed_empty` reason/message, or an RSS entry-limit `WARNING` for the same URL. Unchanged content cannot prove recovery. `HTTPNotModifiedError` identifies the URL and whether it is the primary resource; duplicate-only publication and secondary-resource 304s do not retain prior source health.
- Validator state is source-keyed runtime data, independent of task retention, exposed as worker-only `http_validators` and returned in task results. Do not put it in editable parameters or derive it from task times.
- Fetch/parse/publish failures propagate to `collector_task` and persist FAILURE. Post-collection bots receive only IDs successfully committed during this run, including progress before partial ingestion failure; no affected IDs means no bot dispatch. Cleanup must still run and must not return from `finally`. See [Fuzzy Deduplication](fuzzy-deduplication.md) for content-change detection.

## Network Failures

Direct requests and icons share the task's external Niquests pool; cookies persist only within a redirect chain. Session ownership and connect/read timeout policy are defined in [HTTP Client Lifetimes](http-clients.md). HTTP validators remain request-local and retain the contracts above.

Connection failures/timeouts in `send_get_request` return static DNS/network/`PROXY_SERVER` guidance without claiming a definite cause or retrying. Log details at ERROR and tracebacks at DEBUG; suppress displayed exception chains. Preserve HTTP request exception types for RT’s per-item fallback. Shared collector tests cover diagnostics/logging; RT tests cover continued collection.

## Date Fallbacks

RSS uses the first parseable nonblank entry date, linked article date, channel `lastBuildDate`, then feed HTTP Last-Modified. The channel fallback also covers feed-content/no-link entries. Digest items start at linked article date. Browser article fallback uses the main navigation response, never secondary responses to update primary validators.

Ignore invalid Last-Modified dates. Parsed offset-aware dates become naive UTC; timezone-less values are treated as UTC. Persist/replay HTTP validator strings unchanged. Normalize legacy aware `last_attempted` to UTC before GMT formatting.

## Code and Tests

Worker: `src/worker/worker/collectors/base_web_collector.py`, `rss_collector.py`, `simple_web_collector.py`, and `collector_tasks.py` in that directory. Core: `src/core/core/model/osint_source.py`, `src/core/core/service/task.py`.

Tests: `src/worker/tests/collectors/test_collector.py`, `src/worker/tests/collectors/test_collector_tasks.py`, `src/core/tests/application/worker_pipeline/test_worker_api.py`. Scheduled collector E2E accepts SUCCESS, NOT_MODIFIED, and WARNING terminal outcomes. See [RSS Source Health](rss-source-health.md) for feed validation.

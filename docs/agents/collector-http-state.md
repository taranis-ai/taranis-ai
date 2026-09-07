# Collector HTTP State

## When To Load
RSS Collector, Simple Web Collector, conditional HTTP requests, ETag, Last-Modified, 304 responses, collector task results, or post-collection bot triggering.

## Expected Behavior
Scheduled RSS and Simple Web collections send the server's previously stored ETag and Last-Modified values as `If-None-Match` and `If-Modified-Since`. Manual collections bypass conditional request headers. ETags are opaque strings, including weak ETags.

ETags belong only to the configured primary feed or web URL. The primary resource's Last-Modified value is sent as `If-Modified-Since` on every direct or browser-backed collector request, including article, digest, attachment, and icon URLs. Only a 200 response from the primary resource replaces the stored validator values. A 304 response preserves the validators and is recorded as `NOT_MODIFIED`. If the preceding collection failed, unchanged content cannot establish recovery, so the failure remains in place. If the preceding result reported an empty feed, its `rss_feed_empty` reason and message remain in place.

Browser-backed article fetches use the main navigation response's Last-Modified header as the news item's published-date fallback. Invalid Last-Modified values are ignored in all fetch modes. RSS entry dates use the first parseable, non-blank value from the supported entry fields, linked article date, channel `lastBuildDate`, and feed response HTTP Last-Modified validator; the channel fallback also applies when feed content is used or an entry has no link. Digest-split items use the linked article date, channel `lastBuildDate`, and feed response HTTP Last-Modified validator in that order. Secondary browser responses do not update the primary resource's persisted HTTP validators.

Parsed collector timestamps with an offset are converted to naive UTC; timezone-less values remain unchanged and are treated as UTC. Persisted HTTP Last-Modified validators remain opaque strings and are replayed unchanged. Legacy offset-aware `last_attempted` values are converted to UTC before formatting `If-Modified-Since` with a GMT suffix.

Collector fetch, parse, and publish failures propagate to `collector_task`, which persists `FAILURE` and does not schedule post-collection bots. Playwright cleanup still runs on failures.

## Code Paths
- Worker HTTP behavior: `src/worker/worker/collectors/base_web_collector.py`
- RSS collection and cleanup: `src/worker/worker/collectors/rss_collector.py`
- Simple Web collection: `src/worker/worker/collectors/simple_web_collector.py`
- Task result propagation: `src/worker/worker/collectors/collector_tasks.py`
- Persistent HTTP state: `src/core/core/model/osint_source.py`
- Task-result state update: `src/core/core/service/task.py`

## Data Flow
Core returns a source's `collector_http_state` as `http_validators` in worker-only source data. The collector matches the stored URL to its configured primary URL before replaying the ETag to that URL and Last-Modified to all collector GETs. Collector task results, including empty-feed and preserved failure results, carry the current validator state back to core, where it updates the source-keyed runtime-state row independently of task-history retention.

## Testing
- Worker collector and task regressions: `src/worker/tests/collectors/test_collector.py`, `src/worker/tests/collectors/test_collector_tasks.py`
- Core persistence and worker-source response: `src/core/tests/application/worker_pipeline/test_worker_api.py`
- Scheduled collector E2E checks treat both `SUCCESS` and `NOT_MODIFIED` as successful terminal outcomes.
- Run focused tests while iterating, then the full worker and core suites, component Ruff checks, and `./dev/check_pyrefly.sh`.

## Pitfalls
Do not derive `If-Modified-Since` from task execution timestamps or put validator state in user-editable collector parameters. Do not let secondary responses replace the primary resource's persisted validators. A 304 after an invalid or otherwise failed response must not turn the source successful. Do not return from a cleanup `finally` block.

# Analyze Reports

## When To Load

Analyze lists, report editors, story-count sorting, report-type choices, or the report Publish dialog.

## Contracts

- Lists load Story IDs and report-type titles without Story content or report attributes. Sort in SQL before paging, with a direction-matching Report ID tie breaker and ACL/TLP-filtered counts.
- `/api/analyze/report-editors/<id>` returns form attributes, used Story IDs, revision count, and Story summaries (`id`, `title`, `summary`, `important`, `links`). It shares the full report endpoint's ACL/TLP checks. Its user-scoped `report_editor` cache is separate from full reports and invalidates on Report, Story, and access changes.
- Report-type `needs_review` is true for a required field or Story field; keep it aligned with [Analyst Review](analyst-review.md).
- Editing requires `ANALYZE_ACCESS`. The Publish dialog additionally requires `PUBLISH_ACCESS`; other users skip its catalog lookup. `/api/publish/product-choices` returns every visible Product's ID/title and Type title, ordered by title/ID, without renders or presenter parameters. It shares the `product` list-cache namespace with an endpoint-specific key.
- Search debounces at 250 ms and preserves native GET submission.
- Choose product opens the publishing product chooser; Add to report in Assess attaches the selected stories without sharing them through a connector.

## Entry Points and Coverage

Core: `src/core/core/api/analyze.py`, `publish.py`, and their Report/Product models. Frontend: `src/frontend/frontend/views/report_views.py`; shared contracts: `src/models/models/report.py` and `product.py`.

Coverage: `test_analyze_api.py`, `test_publish_api.py`, `test_rbac.py`, `test_cache_invalidation.py`, `test_report_view.py`, and the `test_user_analyze` browser workflow.

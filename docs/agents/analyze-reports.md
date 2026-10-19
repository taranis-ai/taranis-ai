# Analyze Reports

## When To Load

Analyze lists, report editors, story-count sorting, report-type choices, or the report Publish dialog.

## Contracts

- Report lists batch-load only linked Story IDs and the report-type title; they do not load Story content or report attributes. Story-count ordering runs in SQL before pagination. All sorts end in a direction-matching Report ID tie breaker, including tied titles and creation times. Counts retain the full ACL/TLP-filtered query.
- `/api/analyze/report-editors/<id>` supplies the report form with its ordinary attributes, used Story IDs, revision count, and Story summaries (`id`, `title`, `summary`, `important`, `links`). It shares the full report endpoint's read ACL/TLP checks and 403/404 behavior. The full report API remains available to other callers.
- Editor responses use the separate user-scoped `report_editor` cache namespace. Report writes, Story writes, and user-access changes invalidate it. Do not reuse a summary response as the full report cache entry.
- `/api/analyze/report-types` computes `needs_review` with SQL EXISTS: a required field or any Story field requires guided review. Keep the field rules aligned with [Analyst Review](analyst-review.md).
- `/api/publish/product-choices` requires `PUBLISH_ACCESS` and returns every ACL-visible Product's ID/title and Product Type title, ordered by title/ID. It supplies the report Publish dialog without loading Product renders, report associations, or presenter parameters. Its list cache shares the `product` namespace with an endpoint-specific key, so Product and access changes invalidate both.
- Ordinary Product serialization excludes deferred `render_result` before reading columns. Product detail/render endpoints still return the render deliberately.
- Analyze search uses a 250 ms debounce and retains native GET form submission and targeted table replacement.

## Entry Points and Coverage

Core: `src/core/core/model/report_item.py`, `report_item_type.py`, `product.py`, `base_model.py`; routes in `src/core/core/api/analyze.py` and `publish.py`; cache scopes in `src/core/core/service/cache_invalidation.py`.

Shared contracts: `src/models/models/report.py`, `product.py`. Frontend: `src/frontend/frontend/views/report_views.py`, `src/frontend/frontend/templates/analyze/`.

Coverage: `src/core/tests/application/user_workspace/analysis/test_analyze_api.py`, `src/core/tests/application/user_workspace/publishing/test_publish_api.py`, `src/core/tests/application/mixed_flows/security/test_rbac.py`, `src/core/tests/unit/test_cache_invalidation.py`, `src/frontend/tests/unit/views/test_report_view.py`, and `test_user_analyze` in `src/frontend/tests/playwright/test_e2e_user.py`.

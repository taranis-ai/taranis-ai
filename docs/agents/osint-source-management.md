# OSINT Source Management

## When To Load

Source administration, bulk creation/deletion, curated lists, source groups, `/admin/sources`, rolling collection metrics, or version-4 source import.

## Contracts

- Bulk creation requires at least two URL-based sources sharing all settings except name/primary URL. Supported collectors: RSS, Simple Web, Request Tracker, MISP. Keep the primary-URL mapping explicit; Mastodon/manual/PPN remain single-create.
- Reuse version-4 import for atomic sources and an optional group containing exactly those sources, including normal default-group handling and post-commit scheduling. Do not add a parallel persistence path or merge uploaded files with form defaults.
- Bulk deletion validates all IDs before mutation and commits atomically. `force` accepts only `true`/`false`; it also removes related news and emptied stories. Queue/scheduler/MISP cleanup runs after commit.
- Curated sources/groups use unique stable names as external identities. Loading overlaps/reloads adds missing records/memberships without overwriting fields or removing anything. Renaming catalog entries creates new records on reload.
- A same-name source with a different collector type (even disabled/manual) rejects the entire curated load with 409 and a rename instruction. Ordinary creation may use catalog names.
- Curated loading commits reconciliation, then schedules every selected enabled source. Scheduling failure returns 503 without undoing data; repeat loads retry existing sources too. Successful loads invalidate source/group caches.
- Bulk input errors return 400, core failures retain their status, and transport failures return 502 with the form notification.
- Detail Collect preserves unsaved edits with a notification-only response. Row/Collect All refresh the table; Collect All retains query parameters. Apply the [shared swap/error rules](frontend-development.md).

- Source details show rolling collection counts for the trailing 24 hours, 7 days, or 30 days, defaulting to week, alongside the lifetime news-item count. Use `NewsItem.collected`, never `NewsItem.published`.

## Entry Points and Coverage

`src/frontend/frontend/views/admin_views/source_views.py`, `src/frontend/frontend/templates/osint_source/`, `src/core/core/model/osint_source.py`, `src/core/core/api/config.py`, `src/core/core/static/curated_osint_sources.json`.

The bulk parameter fragment omits only the primary URL; ordinary requests, including `bulk=false`, retain it. Frontend builds the version-4 payload from name/URL rows and shared settings.

Tests: `src/frontend/tests/unit/views/test_views.py`, `src/core/tests/application/admin_console/configuration/test_config_api.py`, and `test_admin_osint_workflow` in `src/frontend/tests/playwright/test_e2e_admin.py`. In E2E, run Collect All before loading curated feeds while only the manual source exists; asynchronous feed collection can otherwise recreate cleaned-up stories and contaminate later workflows.

`GET /config/osint-sources/{id}?period=day|week|month` adds the rolling metric alongside `news_items_count`; the overview does not calculate or return collection activity. Count and period validation live in `src/core/core/model/osint_source.py`; the UI lives in `src/frontend/frontend/templates/osint_source/osint_source_form.html`.

Rolling-window and invalid-period coverage lives in `src/core/tests/application/admin_console/configuration/test_osint_source_validation.py`; detail rendering and period selection are covered in `src/frontend/tests/unit/views/test_views.py`.

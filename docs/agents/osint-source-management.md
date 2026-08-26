# OSINT Source Management

## When To Load

OSINT source administration, bulk source creation, source imports, source groups, collector parameters, `/admin/sources`, or `/config/import-osint-sources`.

## Expected Behavior

Administrators can create one source with the standard source form or bulk-create at least two URL-based sources. Bulk sources share their description, rank, icon, collector type, and every collector parameter except the primary source URL. RSS, Simple Web, Request Tracker, and MISP collectors are supported; manual and PPN sources remain single-create workflows.

Bulk creation can also create one named source group containing exactly the new sources. Source and group persistence is atomic through the existing version-4 source import operation. Import templating or merging imported files with form defaults is not part of this workflow.

## Code Paths

- Frontend view and payload construction: `src/frontend/frontend/views/admin_views/source_views.py`
- Frontend routes: `src/frontend/frontend/router/admin.py`
- Bulk form and source-list entry point: `src/frontend/frontend/templates/osint_source/`
- Transactional import and source-group association: `src/core/core/model/osint_source.py`
- Import API: `src/core/core/api/config.py`

## Data Flow

The bulk form uses Alpine only for adding and removing local name/URL rows. Selecting a collector loads its shared parameter fragment over HTMX with the collector's primary URL parameter omitted; regular parameter requests, including an explicit `bulk=false`, keep the URL field. On submit, the frontend builds a version-4 import payload by combining each name/URL pair with the shared settings. Optional group indexes associate the newly inserted sources with the new group in the same core database transaction.

## Testing

Frontend unit coverage verifies supported collectors, bulk-only parameter omission, and the generated import payload in `src/frontend/tests/unit/views/test_views.py`. The admin browser workflow in `src/frontend/tests/playwright/test_e2e_admin.py` verifies creation, persisted source rows, group membership, and cleanup.

Run `cd src/frontend && uv run pytest tests/unit/views/test_views.py` for focused view coverage. Run the focused admin browser test through the frontend E2E setup for the complete workflow.

## Pitfalls

Keep the collector-to-primary-URL mapping explicit. A collector without a single primary URL should not appear in the bulk form. Do not create a second persistence path: version-4 import already validates sources, creates optional groups, applies default-group membership, commits atomically, and schedules the new sources after the commit.

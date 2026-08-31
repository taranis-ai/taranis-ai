# OSINT Source Management

## When To Load

OSINT source administration, bulk source creation, source imports, curated source lists, source groups, collector parameters, `/admin/sources`, `/config/import-osint-sources`, or `/config/curated-osint-source-lists`.

## Expected Behavior

Administrators can create one source with the standard source form or bulk-create at least two URL-based sources. Bulk sources share their description, rank, icon, collector type, and every collector parameter except the primary source URL. RSS, Simple Web, Request Tracker, and MISP collectors are supported for bulk creation; Mastodon, manual, and PPN sources remain single-create workflows.

The standard create form links from the collector selector to the public collector documentation in a new browser tab.

Bulk creation can also create one named source group containing exactly the new sources. Source and group persistence is atomic through the existing version-4 source import operation. Import templating or merging imported files with form defaults is not part of this workflow.

Bulk deletion validates the complete source selection before changing data and commits all database deletions atomically. The optional `force` query parameter accepts only `true` or `false`; forced deletion also removes related news items and stories left without news items. Queue, scheduler, and MISP job cleanup runs after the database commit.

Administrators can add one or more bundled curated source lists at any time. Catalog source and list IDs become stable database keys, while source and group names remain user-editable. Loading overlapping or previously loaded lists creates each source once, adopts exactly one unkeyed source with the same collector type and primary URL, and adds missing group memberships. Reloading never overwrites user-edited fields or removes sources or memberships. Ambiguous legacy matches fail atomically.

Invalid bulk form input returns HTTP 400. Core import failures preserve the upstream status so monitoring and callers can distinguish validation failures from service failures; transport failures return HTTP 502 while re-rendering the form with a static error.

## Code Paths

- Frontend view and payload construction: `src/frontend/frontend/views/admin_views/source_views.py`
- Frontend routes: `src/frontend/frontend/router/admin.py`
- Bulk form and source-list entry point: `src/frontend/frontend/templates/osint_source/`
- Transactional import and source-group association: `src/core/core/model/osint_source.py`
- Atomic source deletion: `src/core/core/model/osint_source.py`
- Import API: `src/core/core/api/config.py`
- Bundled curated catalog: `src/core/core/static/curated_osint_sources.json`

## Data Flow

The bulk form uses Alpine only for adding and removing local name/URL rows. Selecting a collector loads its shared parameter fragment over HTMX with the collector's primary URL parameter omitted; regular parameter requests, including an explicit `bulk=false`, keep the URL field. On submit, the frontend builds a version-4 import payload by combining each name/URL pair with the shared settings. Optional group indexes associate the newly inserted sources with the new group in the same core database transaction.

The curated-list form is loaded into the admin form container over HTMX. Core reads and validates the bundled catalog, resolves the union of selected source keys, adopts or creates sources, and creates or relinks keyed groups in one transaction. Only newly created sources are scheduled after commit. Frontend source and source-group caches are invalidated after success.

## Testing

Frontend unit coverage verifies the create-form documentation link, supported collectors, bulk-only parameter omission, and Core failure status handling in `src/frontend/tests/unit/views/test_views.py`.

Core API coverage verifies explicit force parsing, all-ID validation, atomic failure behavior, and forced deletion in `src/core/tests/application/admin_console/configuration/test_config_api.py`.

The same core API suite covers overlapping curated lists, idempotent reloads, preservation of edits, membership repair, legacy adoption, and ambiguous-match rollback. Frontend unit and admin browser coverage exercise the multi-select workflow and its safe failure state.

Run `cd src/frontend && uv run pytest tests/unit/views/test_views.py` for focused view coverage. Run the focused admin browser test through the frontend E2E setup for the complete workflow.

## Pitfalls

Keep the collector-to-primary-URL mapping explicit. A collector without a single primary URL should not appear in the bulk form. Do not create a second persistence path: version-4 import already validates sources, creates optional groups, applies default-group membership, commits atomically, and schedules the new sources after the commit.

Curated loading is intentionally separate from arbitrary file import because it must reconcile stable catalog identities. Match legacy sources by exact trimmed primary URL and collector type; do not normalize URLs or match by editable names. Preserve keyed group names and descriptions on every reload.

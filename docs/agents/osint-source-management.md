# OSINT Source Management

## When To Load

OSINT source administration, bulk source creation, source imports, curated source lists, source groups, collector parameters, `/admin/sources`, `/config/import-osint-sources`, or `/config/curated-osint-source-lists`.

## Expected Behavior

Administrators can create one source with the standard source form or bulk-create at least two URL-based sources. Bulk sources share their description, rank, icon, collector type, and every collector parameter except the primary source URL. RSS, Simple Web, Request Tracker, and MISP collectors are supported for bulk creation; Mastodon, manual, and PPN sources remain single-create workflows.

The standard create form links from the collector selector to the public collector documentation in a new browser tab.

Bulk creation can also create one named source group containing exactly the new sources. Source and group persistence is atomic through the existing version-4 source import operation. Import templating or merging imported files with form defaults is not part of this workflow.

Bulk deletion validates the complete source selection before changing data and commits all database deletions atomically. The optional `force` query parameter accepts only `true` or `false`; forced deletion also removes related news items and stories left without news items. Queue, scheduler, and MISP job cleanup runs after the database commit.

Administrators can add one or more bundled curated source lists at any time. Source and group names are unique and deliberately serve as the stable external identities instead of a separate index or key. This prevents duplicate names when defaults or source files are loaded repeatedly, lets the curated loader reuse records by name, and allows the same externally managed JSON definitions to be used across instances without relying on database IDs. Loading overlapping or previously loaded lists creates each source once and adds missing group memberships. Reloading never overwrites existing source or group fields and never removes sources or memberships.

The OSINT source table keeps actions in its primary toolbar. Search, manual-source visibility, and status share a unified query row directly above the table. The creation buttons use the page context to keep their labels concise: New source and Curated sources.

The bundled catalog groups sources into Austrian news and public-sector coverage, cyber threat intelligence, technology news, security advisories, original threat research, cybersecurity news, vendor research, vulnerability intelligence, independent experts and community sources, and a balanced starter pack. Curated feeds are selected for authority, current parseability, recency, and useful coverage. High-volume vulnerability feeds remain in their own opt-in list.

Invalid bulk form input returns HTTP 400. Core import failures preserve the upstream status so monitoring and callers can distinguish validation failures from service failures; transport failures return HTTP 502 while re-rendering the form with a static error.

Curated loading rejects a same-name source with a different collector type, including enabled or disabled manual sources, with HTTP 409 before committing. The error identifies the source and asks the administrator to rename it before retrying. The entire load is rolled back; ordinary source creation still allows names found in the catalog.

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

The curated-list form is loaded into the admin form container over HTMX. Core reads and validates the bundled catalog, resolves selected lists and sources by name, and creates or relinks them in one transaction. After commit, Core schedules every selected enabled source. A scheduling failure returns HTTP 503 without undoing the committed data; repeating the same load retries scheduling for both new and existing sources. Frontend source and source-group caches are invalidated after success.

## Testing

Frontend unit coverage verifies the create-form documentation link, supported collectors, bulk-only parameter omission, and Core failure status handling in `src/frontend/tests/unit/views/test_views.py`.

Core API coverage verifies explicit force parsing, all-ID validation, atomic failure behavior, forced deletion, and curated-list collector-type conflicts and atomic rejection in `src/core/tests/application/admin_console/configuration/test_config_api.py`.

Admin browser coverage exercises the curated multi-select workflow.

## Pitfalls

Keep the collector-to-primary-URL mapping explicit. A collector without a single primary URL should not appear in the bulk form. Do not create a second persistence path: version-4 import already validates sources, creates optional groups, applies default-group membership, commits atomically, and schedules the new sources after the commit.

Curated loading is intentionally separate from arbitrary file import because it reconciles existing sources and groups by their unique names. Keep catalog source and list names stable; changing one creates a new database record on the next load. A separate immutable key was considered for this identity but rejected as unnecessary while names are unique and stable; do not introduce another required identifier unless names can no longer satisfy that contract.

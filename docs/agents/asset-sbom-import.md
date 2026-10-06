# Asset SBOM Import

## When To Load

Asset SBOM uploads, software inventory, CPE coverage, import confirmation, component triggers, or asset intelligence matching.

## Contracts

- Core consumes CycloneDX JSON 1.5–1.7. Validation covers the inventory fields used by the importer, not the entire CycloneDX schema. Require at least one syntactically valid CPE on software; accept formatted CPE 2.3 and CPE URI names. No external lookup verifies product identity.
- Import one application/system asset. Exclude `file` components while still traversing their children. A file-type metadata root is the scan target, not an excluded inventory record. Include non-file metadata components.
- Group software by canonical package URL, component type, and version. Without a package URL, require matching type, namespace/group, name, version, suppliers, and CPEs. Retain each original component reference and Syft installation path. Never collapse solely by display name.
- Read CPEs from both `cpe` and Syft `syft:cpe23` properties. Preserve invalid values for preview warnings; persist valid values in component inventory and a deduplicated asset-level CPE projection for existing report associations. CPE-free software remains in inventory and receives disabled name/supplier suggestions.
- Upload and preview require `ASSETS_CREATE`; drafts belong to their importing user and organization. Confirmation rechecks destination group access, locks the import, and atomically creates the asset. Repeated confirmation returns the existing asset. The same user's repeated identical upload resumes its accessible import. This is not an SBOM update/merge interface.
- Drafts expire after 24 hours and expired drafts are deleted on subsequent valid uploads. Confirmed imports remain with the asset; deleting the asset cascades its inventory. Inventory reads require `ASSETS_ACCESS` and current asset-group access. Import provenance records uploader, organization, filename, SHA-256, upload/confirmation times, document serial/version, and generation time. Original file bytes are not retained.
- Core, frontend, and bundled production/development Nginx default to a 250 MiB request limit (including multipart overhead). The upload page reads the frontend limit from configuration. Keep all three layers aligned when overriding the limit. The parser bounds component count and nesting, and inventory responses paginate at 50 grouped components. The representative external Syft sample is roughly 46 MiB with about 78,000 component records, predominantly files; do not commit that full host inventory.

## Triggers and Intelligence

- Preview includes suggestions derived from component names, suppliers and CPE products/vendors. Confirmation saves them with their component and provenance (`sbom`, `cpe`, `supplier`). All suggestions start disabled. External enrichment is outside the PoC. Analysts can add aliases (`analyst`), edit phrases/context, and enable or disable selected rules. Generation only fills missing suggestions using their original key, preserving reviewed, edited and disabled rules.
- Matching uses literal case-insensitive phrases with Unicode word boundaries and flexible whitespace. Context is an OR list: at least one context phrase must occur in the same article's title or content. The Python `requests` suggestion starts with `Python` context. Installed versions remain part of component identity but are not mandatory matching terms. HTML attributes and script/style text are not article evidence.
- Collection creates/replaces evidence in Core's ingestion transaction. Story and article edits also refresh it. Matches retain article IDs, trigger/component associations, the literal matching text, field and excerpt. The asset intelligence view groups by current story membership; grouping/ungrouping does not detach evidence. Mentions never create vulnerability findings or change the existing report-based vulnerability count.
- Historical scans are explicit RQ `misc` jobs (`asset_match_task`). Default scope is articles collected in the last 30 days; 0 means all history. Core processes 200 articles per batch up to the scan's start time, persists a UUID cursor, and rechecks the requesting user's permissions and visibility on each batch. Progress is shown only to the initiating user; refresh the results page to update status. A failed run can be replaced by a new scan. A worker killed before reporting failure can leave a run pending; restart the scan in that case.
- Trigger edits remove that trigger's old evidence; disabling removes its matches immediately. Re-enabling affects future collection; scan history after rule changes. Evidence reads recheck current text/context, source ACLs, canonical `Story.visible_query`, and individual article TLP to suppress stale or inaccessible results. Matching is potential relevance, not proof that the installed version is vulnerable.
- Reads require `ASSETS_ACCESS` and current asset-group access; intelligence/status also require `ASSESS_ACCESS`. Trigger writes use `ASSETS_CREATE`; historical scans also require `ASSESS_ACCESS`. API-key batch endpoints cannot elevate the initiating user's scope. Frontend calls bypass caches deliberately so permissions and reviewed rule/evidence state are current. Rules paginate at 50 and intelligence at 20 stories.
- The PoC covers issue #1121 steps 1–4. Updating an existing asset with a different SBOM (step 5) is not implemented. Identical uploads still resume an accessible import. Deleting an asset cascades inventory, triggers, matches, and historical runs.

## Local PoC Walkthrough

1. Open **Assets → Import SBOM**, select a CycloneDX JSON file, and preview the component/CPE coverage and disabled suggestions.
2. Confirm the application or host name and destination group, then create the asset.
3. Open **Component triggers**, search for a product such as `openssl`, and enable the relevant component rules. Expand **Edit trigger** to change phrases or add one context phrase per line; **Add alias for this component** creates an analyst rule.
4. Open **Relevant intelligence → Scan existing articles**, choose the collection lookback, and use **Refresh results** until the scan completes. New or changed collected articles are matched automatically. Follow a supporting article link to inspect its evidence in Assess.

The scan needs a running worker subscribed to `misc`. Restart Core after applying the feature so metadata creates the new tables; restart the frontend and worker to load their changes. Follow the developer's chosen local startup workflow. No external scanner or enrichment service is needed.

## Entry Points and Coverage

Core: `core/service/sbom.py`, `core/api/asset_sbom.py`, `core/model/asset_sbom.py`, and `asset_intelligence.py` in each of those layers. Shared contracts: `models/sbom.py`, `models/asset_intelligence.py`. Frontend: `views/asset_sbom_views.py`, `views/asset_intelligence_views.py`, and `templates/assets/`. Worker: `worker/misc/asset_matching.py`.

Core coverage: `tests/application/test_asset_sbom.py` covers import, review/provenance, contextual collection matching, grouped evidence, idempotent historical batches, and organization/ACL/TLP restrictions. Its small portable fixture remains `src/core/tests/test_data/sbom/software.cdx.json`.

The full-stack browser workflow `tests/playwright/test_e2e_asset_sbom.py` serves both CI and the recorded showcase using the shared highlight/delay helpers. Its small `src/core/tests/test_data/sbom/test-sbom-import.cdx.json` retains representative BuildKit identities and installation paths from the external host sample. `tests/playwright/testdata/sbom-news-items.json` supplies title/body matches plus partial-name, missing-context, and disabled-component negatives. News is ingested before trigger review to exercise a real queued historical scan; later ingestion updates and rule disabling remove evidence. This workflow uses a fresh isolated stack and needs no local data. Recording instructions are in the [Playwright guide](../../src/frontend/tests/playwright/README.md#record-the-sbom-poc-walkthrough).

See [Architecture and Boundaries](architecture-and-boundaries.md), [RBAC ACL Behavior](rbac-acl.md), and [Development Workflow](development-workflow.md).

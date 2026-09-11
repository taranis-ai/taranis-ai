# Story Export

## When To Load
Settings story transfers, Assess card/bulk JSON sharing, story serializers, and export date filters.

## Contracts
- Settings uses `settings/settings.html` → `settings/story_transfer.html` → the admin settings download proxy → Core `/api/settings/export-stories`. This requires `ADMIN_OPERATIONS` and exports the instance, without content ACL filtering.
- Settings downloads remain JSON arrays. The minimal format contains story ID, UTC creation time, and news-item ID/title/content. Metadata export adds story attributes and retains its existing fields, including detailed news items. Neither export calls `to_detail_dict()` or queries report counts.
- Date inputs are explicitly UTC. Core accepts offset-aware dates and normalizes them to UTC; bounds are inclusive and apply to `Story.created`. Blank bounds are optional, future dates and reversed ranges are errors. A From-only range ends at the current time.
- Assess cards and bulk sharing use `story_actions.html` → the sharing dialog/page → frontend `/story/export` → Core `/api/assess/stories/export`. Downloads bypass frontend story caches and list pagination. They keep the `{total_count, items}` envelope and shared model import allowlists, including story/news-item attributes and news-item tags.
- Selected exports require `ASSESS_ACCESS`, story and news-item TLP access, and read access to every linked source. Missing or inaccessible selections return a generic 404 without downloading a partial file. Repeated IDs are deduplicated; selection order is retained. Read-only source ACLs permit export.
- `Story.to_export_dict()` adds attributes to the base payload without UI-only detail counts. Worker payload maps remain distinct because NLP/MISP consumers require them. Export relationships are loaded in batches.
- Local news-item order is reflected in exported arrays, but the local order column is excluded and is not restored on import. These transfers are content exports, not full database backups; user votes, bookmarks, and report relationships are not restored.

## Entry Points and Validation
`src/core/core/model/story.py`, `src/core/core/service/story.py`, `src/core/core/service/admin.py`, `src/core/core/api/assess.py`, `src/models/models/admin.py`, and frontend `story_views.py`/`admin_views/settings_views.py`.

Existing core Assess/admin API suites cover metadata, import persistence, complete selections beyond 400 stories, and date boundaries. The RBAC suite covers mixed-source and TLP denials. Frontend view tests cover streamed downloads and errors; `test_story_export` and the admin settings browser workflow exercise the actual links/forms. Use the normal full feature signoff pipeline.

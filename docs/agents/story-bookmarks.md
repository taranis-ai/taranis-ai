# Story Bookmarks

## When To Load

Bookmark collections, `/bookmarks`, Assess bookmark bar/dialog, story bookmarking, or bookmark cache/context changes.

## Contracts

- Collections are private per user, with unique names and user-defined positions. Reordering posts `bookmark_ids` to `/assess/bookmarks/order`; core scopes IDs to the current user.
- The searchable picker adds/removes multiple collection memberships and creates an optional collection in one Core transaction. Fully shared memberships start checked; partially shared memberships start indeterminate and stay unchanged unless toggled. Frontend derives removals from initially fully selected collections and explicit partial removals; filtering the picker never removes hidden choices. Failures keep the dialog and inputs open; standalone retries also restore explicit partial removals and determinate choices.
- Quick-save uses `ProfileSettings.default_bookmark_id`, independently of collection order. An absent/deleted/inaccessible default falls back to the user's literal `Bookmarks` collection (creating it if needed) and persists that choice. Default updates validate collection ownership. Deleting the default clears the preference. No schema migration is needed.
- Story list/detail `bookmarked` state is private to the requesting user; lists batch the membership query. Saved card actions remove the story from all of the user's collections in one membership update. Collection management remains available through the selection bar's picker and quick-save feedback's Change action. Successful changes return OOB action replacements and the Assess collection bar, preserving selection, filters, and scroll. Quick-save feedback names the destination and offers Change plus Undo only when this request added the membership. Undo removes only that collection membership.
- Assess shows at most six collections ordered by position and links to all bookmarks. Every mutation, including reorder and story membership changes, invalidates bookmark and story caches. Default-changing endpoints also invalidate the owning user profile cache.
- Bookmark selection uses visible card checkboxes associated with a separate native form, keeping per-card mutation forms unnested. HTMX action includes must explicitly select both that form and the checked `story_ids` inputs: HTMX 4 omits externally associated controls when only the form is included. Per-card Read/Important requests include checked IDs so replacement cards retain selection.
- Detail pages reuse Assess cards and selection controls but omit Bookmark/`Shift+B`, keep Read/Important alongside Remove selected, and show Read/Important/In Reports even with compact cards. Follow [shared selection and form rules](frontend-development.md).
- Bulk actions, report/clustering dialogs, Ungroup, and editor replacements/saves carry `bookmark_id` to preserve the current collection, return link, and visible selection on success or failure. `Cluster and Open` deliberately navigates to the primary story.
- Instant bookmark and editor Save work as normal POST forms as well as HTMX actions; bookmark saves retain their return target.
- Query cards through the canonical Assess collection using the bookmark's ordered story IDs. Embedded bookmark `stories` lack Assess enrichment such as `in_reports_count`.
- Core rejects ungrouping report-assigned stories. Eligible ungrouping replaces bookmark membership with the new standalone stories in the same transaction; partial ACL-limited ungrouping also retains a non-empty original story.

## Entry Points

- Core API/model: `src/core/core/api/assess.py`, `src/core/core/model/story.py`
- Shared contract: `src/models/models/assess.py`
- Frontend: `src/frontend/frontend/views/story_bookmark_views.py`, `src/frontend/frontend/views/story_views.py` (`rerender_list`)
- Templates: `src/frontend/frontend/templates/bookmarks/`, `src/frontend/frontend/templates/assess/bookmarks_bar.html`

## Coverage

`src/core/tests/application/user_workspace/assessment/test_story_bookmarks.py`; `src/frontend/tests/unit/views/test_story_bookmark_view.py`; `src/frontend/tests/unit/views/test_story_view.py`; bookmark workflows in `src/frontend/tests/playwright/test_e2e_workflow.py` and `src/frontend/tests/playwright/test_no_javascript.py`.

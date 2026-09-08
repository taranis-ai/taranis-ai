# Story Bookmarks

## When To Load

Bookmark collections, `/bookmarks`, Assess bookmark bar/dialog, story bookmarking, or bookmark cache/context changes.

## Contracts

- Collections are private per user, with unique names and user-defined positions. Reordering posts `bookmark_ids` to `/assess/bookmarks/order`; core scopes IDs to the current user.
- Modal bookmarking chooses/creates a collection for selected stories. Instant bookmarking uses the earliest collection or creates the literal default name `Bookmarks`. UI labels remain translatable; that stored default name is a contract.
- Assess shows at most six collections ordered by position and links to all bookmarks. Every mutation, including reorder and story membership changes, invalidates the bookmark cache.
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

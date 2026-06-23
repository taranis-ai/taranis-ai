# Story Bookmarks

## When To Load

Load this memory for tasks mentioning bookmark collections, bookmarks, `/bookmarks`, Assess bookmark bars, instant story bookmarking, the bookmark dialog, adding or removing stories from a collection, or bookmark-related cache invalidation and translations.

## Expected Behavior

Bookmark collections are user-private Assess data. Core exposes list, detail, create, rename, delete, add-stories, and remove-stories operations for them.

The frontend supports two bookmark entry paths:

- the modal flow for selecting one or more stories and choosing an existing or new collection
- the instant single-story flow that uses the first available collection or creates a default collection named `Bookmarks`

The Assess page shows a compact bookmark bar with up to six collections ordered by user-defined bookmark position and an `All bookmarks` link. Bookmark labels in templates should stay translatable, but the default collection name used by the instant create path stays `Bookmarks`.

Bookmark detail views reuse Assess story cards, but hide the per-story `Bookmark` action because those stories are already in a bookmark collection.

## Code Paths

- Core API: `src/core/core/api/assess.py`
  - `StoryBookmarks`
  - `StoryBookmark`
  - `StoryBookmarkStories`
  - `StoryBookmarkStoryRemoval`
- Core model: `src/core/core/model/story.py`
  - `StoryBookmark`
  - user scoping, uniqueness, and ordering
- Shared models: `src/models/models/assess.py`
  - `StoryBookmarkBase`
  - `StoryBookmarkCreatePayload`
  - `StoryBookmarkUpdatePayload`
  - `StoryBookmarkStoryPayload`
  - `StoryBookmark`
- Frontend views: `src/frontend/frontend/views/story_bookmark_views.py`, `src/frontend/frontend/views/story_views.py`
- Frontend routes: `src/frontend/frontend/router/assess.py`
- Templates: `src/frontend/frontend/templates/bookmarks/`, `src/frontend/frontend/templates/assess/bookmarks_bar.html`, `src/frontend/frontend/templates/assess/story_actions.html`
- Tests:
  - `src/core/tests/application/user_workspace/assessment/test_story_bookmarks.py`
  - `src/frontend/tests/unit/views/test_story_bookmark_view.py`
  - `src/frontend/tests/unit/views/test_story_view.py`
  - `src/frontend/tests/playwright/test_e2e_workflow.py`

## Data Flow

`StoryView.get_extra_context()` loads bookmark collections for the Assess bar through `DataPersistenceLayer().get_objects(StoryBookmark, PagingData(limit=6, order="position_asc", ...))`.

Users reorder bookmark collections on `/bookmarks` by dragging cards. The frontend posts the ordered `bookmark_ids` list to `/assess/bookmarks/order`; core scopes the IDs to the current user and persists zero-based `position` values.

Bookmark mutations in the frontend call core through `CoreApi()`, then invalidate the local bookmark cache so list/detail views and the Assess bar can refresh with current data.

The instant bookmark path first looks up the earliest collection, then falls back to creating `Bookmarks` in core if the user has none. The modal flow posts selected story IDs to the existing add-stories endpoint.

## Testing

- Core API coverage: `cd src/core && uv run pytest tests/application/user_workspace/assessment/test_story_bookmarks.py`
- Frontend bookmark views: `cd src/frontend && uv run pytest tests/unit/views/test_story_bookmark_view.py tests/unit/views/test_story_view.py`
- E2E coverage: `cd src/frontend && uv run pytest tests/playwright/test_e2e_workflow.py -k bookmark`
- If bookmark-related template strings change, refresh catalogs with `cd src/frontend && uv run pybabel compile -d frontend/translations`

## Pitfalls

- Do not localize or rename the backend default collection contract without updating the instant-create flow and its tests together.
- Bookmark collections are private per user; cross-user access should stay 404/403 as implemented by the core API.
- Bookmark names are unique per user.
- Keep cache invalidation after create/update/delete/add/remove operations or the frontend will render stale bookmark data.
- Keep cache invalidation after bookmark reorder or the Assess bar and bookmark list can render stale positions.
- The Assess bookmark bar is intentionally capped at six items; do not broaden it without an explicit UI change.
- Keep the Assess `Shift+B` bookmark shortcut guarded by `canUseAssessShortcut`; typing uppercase letters in bookmark dialogs must not reopen toolbar modals.
- Prefer `data-testid` selectors when adding e2e coverage for bookmark behavior.

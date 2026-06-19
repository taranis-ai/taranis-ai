# Assess Filters

## When To Load

Load this memory for tasks mentioning assess filters, the assess sidebar, story filtering, `/assess`, `/api/assess/filter-lists`, `FilterLists`, assess default filters, source/group/language/tag filters, or omnisearch assess filter syntax.

## Expected Behavior

Assess filters let users narrow stories and news items from the assess workspace by search text, read/important/relevant/in-report states, source, group, language, tags, date range, and sorting.

Filter option lists must reflect current user-visible database state. `/api/assess/filter-lists` builds those options on request and returns tags, sources, groups, and languages. The frontend may cache the response per user, so core writes that affect assess views must invalidate the relevant frontend cache scope.

Saved assess default filters belong to the user profile. Applying defaults should preserve the same canonical query parameter shape used by normal sidebar filtering.

## Code Paths

- Core API: `src/core/core/api/assess.py`
  - `/api/assess/filter-lists`
  - story/news item filter argument parsing
- Core filter data: `src/core/core/model/filter_data.py`
- Core cache invalidation: `src/core/core/service/cache_invalidation.py`
- Shared models: `src/models/models/assess.py`
  - `FilterLists`
  - assess source/group/list models
- Frontend API client: `src/frontend/frontend/core_api.py`
- Frontend assess view: `src/frontend/frontend/views/story_views.py`
  - filter-list loading and user cache
  - source/group/language select data
  - saved default filter extraction and redirect URL construction
- Frontend dashboard view: `src/frontend/frontend/views/dashboard_views.py`
  - saved-filter shortcut links
- Frontend routes: `src/frontend/frontend/router/assess.py`
- Omnisearch: `src/frontend/frontend/omnisearch.py`, `src/frontend/frontend/router/base.py`
- Templates: `src/frontend/frontend/templates/assess/sidebar/`
  - `sidebar.html`
  - `source_select.html`
  - `language_select.html`
  - `tags_select.html`
  - `filter_token_select.html`
  - `tri_state_filter.html`
  - `saved_filters_dialog.html`
- Shared saved-filter template: `src/frontend/frontend/templates/assess/saved_filter_cards.html`

## Data Flow

The assess page loads filter lists through `StoryView.get_filter_lists()`. That method first checks the frontend model cache for the current username, then calls `CoreApi().get_filter_lists()`, which requests `/assess/filter-lists` from core.

Core serves filter lists through `FilterLists.get()` in `src/core/core/api/assess.py`, backed by `FilterData.get_assess_filterlists()`.

Sidebar form submissions and saved defaults use query parameters. Multi-value filters such as source, group, language, and tags must stay list-shaped where the view/core expects lists.

The dashboard can surface saved Assess filters as shortcut cards, but should reuse the same saved-filter normalization and canonical `/assess` URL construction instead of adding a dashboard-specific endpoint or payload shape. Show only the first three saved filters by default and put the rest behind the dashboard's native Show more/Show less pattern.

Omnisearch only loads assess filter lists when value resolution or suggestions need them. Keep this lazy behavior so ordinary global search does not always fetch filter-list data.

## Testing

Use focused tests for assess filter changes:

- Core filter-list behavior: `cd src/core && uv run pytest tests/application/user_workspace/assessment/test_story_filters.py`
- Frontend assess view behavior: `cd src/frontend && uv run pytest tests/unit/views/test_story_view.py`
- Omnisearch filter syntax and suggestions: `cd src/frontend && uv run pytest tests/unit/test_omnisearch.py`

For broad validation or CI regressions, follow the project test instructions in `AGENTS.md`.

## Pitfalls

- Do not import admin-domain models from `models.admin` into user-facing frontend assess views.
- Do not use admin/config endpoints for user-facing assess filter workflows.
- Keep frontend and core query parameter names aligned; avoid adding compatibility aliases for new WIP filter fields.
- Filter-list cache invalidation matters because stale sources, groups, tags, or languages can hide available filter options.
- Treat persisted naive datetimes in core as UTC when date/range filtering changes touch stored timestamps.
- Prefer `data-test-id` selectors when adding e2e coverage for new filter UI behavior.

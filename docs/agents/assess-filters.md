# Assess Filters

## When To Load

Assess sidebar/search/default filters, `/assess`, `/api/assess/filter-lists`, omnisearch filter syntax, or pagination.

## Contracts

- Without JavaScript, search and the native sidebar filters submit through one GET form, and the form exposes an explicit Apply filters button. Source, language, group, and tag filters are hidden because their token-selection workflows require JavaScript.
- Filter lists contain current user-visible tags, sources, groups, and languages. Core builds them on request; frontend caches per user. Writes affecting those options must invalidate the relevant frontend scope.
- Sidebar submissions, profile defaults, and dashboard shortcuts share canonical query parameters; source/group/language/tag values remain list-shaped. Saving an existing filter name updates it; identical criteria under a different name are rejected.
- Dashboard shortcuts reuse saved-filter normalization, delete routes, and Assess URLs. Show the first three by default, with the rest behind Show more.
- Omnisearch fetches filter lists lazily, only for value resolution/suggestions.
- Paged navigation replaces `#story-list` and out-of-band `#story-pagination`, scrolls to the top, and keeps the sticky top bar mounted. Errors notify without replacing/appending stories. Stable search-input IDs preserve focus.
- `Shift+Space` prevents native page-up on keydown and performs read/unread on keyup only with a selection. Bookmark detail shares this behavior and the [global shortcut/selection rules](frontend-development.md).
- Successful clustering replaces the saved Assess selection with the first story in the submitted dialog order before the list swap; merged-away IDs must not survive into the next action. Failed clustering preserves selection and the open dialog. `test_user_assess` in `test_e2e_user.py` requires three cards and performs two merges, checking the surviving selection and removal of each secondary card.
- Browser tests use `_get_assess_story_counts` to wait for both Alpine counts; wrapper visibility is insufficient.
- Search submits on debounce and changed-value blur. Before opening card menus, tests wait for filtering and the blur-triggered HTMX request.

## Entry Points

- Core: `src/core/core/api/assess.py`, `src/core/core/model/filter_data.py`, `src/core/core/service/cache_invalidation.py`
- Contract: `src/models/models/assess.py`
- Frontend: `src/frontend/frontend/views/story_views.py` (`get_filter_lists`), `src/frontend/frontend/views/dashboard_views.py`, `src/frontend/frontend/omnisearch.py`
- Templates: `src/frontend/frontend/templates/assess/sidebar/`, `src/frontend/frontend/templates/assess/saved_filter_cards.html`

## Coverage

`src/core/tests/application/user_workspace/assessment/test_story_filters.py`; `src/frontend/tests/unit/views/test_story_view.py`; `src/frontend/tests/unit/test_omnisearch.py`; `src/frontend/tests/playwright/test_main_js.py`; pagination in `test_user_profile` in `src/frontend/tests/playwright/test_e2e_user.py`.

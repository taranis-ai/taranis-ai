# Assess Filters

## When To Load

Assess sidebar/search/default filters, `/assess`, `/api/assess/filter-lists`, omnisearch filter syntax, or pagination.

## Contracts

- Without JavaScript, search and the native sidebar filters submit through one GET form, and the form exposes an explicit Apply filters button. Source, language, group, and tag filters are hidden because their token-selection workflows require JavaScript.
- Filter lists contain at most 1,000 current user-visible options per list, ordered by name (normalized value for languages). Core applies the limit in SQL after visibility filtering. Tags start from distinct non-report names in `NewsItemTagCluster`, then probe indexed tag occurrences for a non-report tag on an ACL/TLP-visible story. Deduplicate candidates before these checks; `OFFSET 0` keeps PostgreSQL from expanding the probes into a full tag-table join. Core builds lists on request; frontend caches per user. Writes affecting those options must invalidate the relevant frontend scope. Chat's reference catalog omits options beyond this cap; direct Assess filters still accept them.
- Assess tag suggestions use `/api/assess/taglist` directly, independently of the filter-list cap/cache. Search matches literal substrings case-insensitively after trimming whitespace. Rank exact names first, then distinct ACL/TLP-visible story counts descending, then case-insensitive name and original name for stable ties; apply pagination afterward (20 suggestions by default). Combine occurrences across tag types, exclude report tags, and count each story once. Frontend forwards the search as an encoded query parameter.
- Tag suggestions return `{name, story_count}` objects; the displayed count reuses the ranking aggregate without extra queries. Counts cover all visible stories bearing that tag, independently of other active sidebar filters. Rows truncate long names to one line, preserve the full name in the button title, and keep the count visible. The Assess browser workflow checks long URLs and names with spaces for truncation and row overlap.
- The remote token control's HTMX request guard reads `this.value`; HTMX inline handlers cannot call Alpine component methods such as `hasQuery()` directly. The Assess browser workflow covers searching and selecting a tag.
- Assess, Chat, and source/group references share `FilterData`, limited to ACL/TLP-visible stories. Sources/groups without visible stories are omitted; reference ACLs still apply.
- Story filters use existence checks for source/language membership, tags, reports, and attributes so matching related rows do not multiply stories. Source/group alternatives and language constraints must match the same news item. ACL and TLP checks remain on the filtered story query.
- Paged user lists select ordered story IDs before loading story content and enriching votes/report counts. Every sort ends with the story ID as a stable tie-breaker. Counters project only ID/read/important, remove ordering/paging, and aggregate the filtered set once; `in_reports_count` retains its report-association count semantics.
- Story views reuse filter lists by user within the current request even with `CACHE_ENABLED=false`. This includes repeated detail/form context construction; subsequent requests still fetch fresh lists when the frontend cache is disabled.
- Failed upstream list loads return a static message and HTTP 502. HTMX receives a notification-only fragment; native navigation renders the Assess page with the error. Filters (including Clear time filters), bulk status actions, and story deletion route 5xx responses to the notification bar without replacing the visible list. Return only the load error even after a successful action; HTMX selects the first notification bar. Never expose exception text.
- Story/report writes also invalidate news-item, bookmark, and filter caches. Admin ACL/role/source/group/settings writes invalidate all frontend caches.
- Bulk story updates reject non-string story IDs with a static 400 before looking up or updating any story. API coverage is in `test_assess_api.py`.
- Sidebar submissions, profile defaults, and dashboard shortcuts share canonical query parameters; source/group/language/tag values remain list-shaped. Saving an existing filter name updates it; identical criteria under a different name are rejected after canonical validation and serialization, including case normalization of choice fields.
- List refreshes after non-GET actions restore the active query from `HX-Current-URL`, including DELETE story actions. Deleting the last matching story leaves the filtered result empty; it must not show unfiltered stories while the sidebar still displays active filters.
- Story cards keep tags matching any active tag-name or tag-type filter visible and highlighted even when collapsed or compact. Card/list replacements after mutations recover active tags from the Assess `HX-Current-URL`, including HTMX PUT actions. Tag expansion is local to the tag list; opening story details shows all tags without the former twenty-tag cap. Coverage belongs to the Assess browser workflow and story view tests.
- Dashboard shortcuts reuse saved-filter normalization, delete routes, and Assess URLs. Show the first three by default, with the rest behind Show more.
- Omnisearch fetches filter lists lazily, only for value resolution/suggestions.
- Paged navigation replaces `#story-list` and out-of-band `#story-pagination`, scrolls to the top, and keeps the sticky top bar mounted. Errors notify without replacing/appending stories. Stable search-input IDs preserve focus.
- Story Open/Edit and the selection shortcut carry a relative `assess_url` through editor layouts, saves, and card replacements. Explicit return URLs take precedence over `HX-Current-URL`, which stays on the initial page during infinite scroll. Back to Assess restores filters and pagination with a native link; only the application's Assess path is accepted. Direct story links fall back to ordinary Assess, and bookmark returns keep their existing destination.
- Assess remembers the latest search in user- and application-path-scoped localStorage. Opening bare Assess offers Restore last search or Dismiss; explicit filters, saved defaults, and reset links take precedence. Pagination updates the stored URL. Storage failures do not affect native return navigation.
- Infinite-scroll searches opened past the first page explain their starting result and offer Start from beginning with the same filters. Counts label the stories actually loaded; the footer range includes all appended batches and End of results does not imply earlier results were loaded.
- `Shift+Space` prevents native page-up on keydown and performs read/unread on keyup only with a selection. Bookmark detail shares this behavior and the [global shortcut/selection rules](frontend-development.md).
- Successful clustering replaces the saved Assess selection with the first story in the submitted dialog order before the list swap; merged-away IDs must not survive into the next action. Failed clustering preserves selection and the open dialog. `test_user_assess` in `test_e2e_user.py` requires three cards and performs two merges, checking the surviving selection and removal of each secondary card.
- The Assess pagination/editing browser workflow reads the stored source ID from its seeded story and filters to that source so scheduled collection from other sources cannot change its expected total.
- Browser tests use `_get_assess_story_counts` to wait for both Alpine counts; wrapper visibility is insufficient.
- Search submits on debounce and changed-value blur. Before opening card menus, tests wait for filtering and the blur-triggered HTMX request.
- `AssessSearchFilters` owns filter validation and serialization for Core, saved filters, and Chat; paging/internal controls stay separate. Chat links use canonical `/assess` queries with doseq encoding.
- Before `Story.get_by_filter(filter_args, current_user)`, Core validates model-proposed source, group, tag, language, and recent-story references against the user's visible catalog. Chat must never bypass this validation or turn proposed filters into raw SQL.

Relative date windows and explicit `timefrom` use the publication-derived story `created` date. Collection changes mark stories unread but do not force old stories into the current Shift window. See [Collection Updates](fuzzy-deduplication.md).

## Entry Points

- Core: `src/core/core/api/assess.py`, `src/core/core/model/filter_data.py`, `src/core/core/service/cache_invalidation.py`
- Contract: `src/models/models/assess.py`
- Frontend: `src/frontend/frontend/views/story_views.py` (`get_filter_lists`), `src/frontend/frontend/views/dashboard_views.py`, `src/frontend/frontend/omnisearch.py`
- Templates: `src/frontend/frontend/templates/assess/sidebar/`, `src/frontend/frontend/templates/assess/saved_filter_cards.html`
- Return navigation and browser search storage: `StoryView._get_assess_return_url`, `src/frontend/frontend/static/js/assess-navigation.js`, `src/frontend/frontend/templates/assess/back_link.html`
- Chat: `src/core/core/service/chat.py`, `src/frontend/frontend/views/chat_views.py`

## Coverage

`src/core/tests/application/user_workspace/assessment/test_story_filters.py`; `src/frontend/tests/unit/views/test_story_view.py`; `src/frontend/tests/unit/test_omnisearch.py`; `src/frontend/tests/playwright/test_main_js.py`; pagination in `test_user_profile` in `src/frontend/tests/playwright/test_e2e_user.py`.

The landing-page workflow's `test_assess` records two unread, unimportant stories being marked read and then important. It selects representative visible cards rather than relying on a fixed seed count. Detailed filtering, bulk actions, clustering, and editing belong to the regular `test_e2e_user.py` workflows rather than the recording.

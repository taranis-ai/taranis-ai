# Assess Filters

Load for: Assess sidebar/search/default filters, `/assess`, `/api/assess/filter-lists`, omnisearch filter syntax, or pagination.

## Contracts

- `classification` uses the eight llm-bot categories in `models/classification.py` across sidebar, saved filters, Chat, and `classification:`/`topic:` omnisearch (quote spaces). Rerun classification and replace binary filters manually. `CYBERSEC_CLASSIFIER_BOT` retains bot IDs/schedules.

- Assess removes empty GET parameter values before rendering. Native navigation redirects to the clean Assess URL; HTMX normalizes request arguments in place and returns `HX-Push-Url` so filters stay asynchronous. Preserve repeated non-empty values and explicit values such as `false` and `0`.
- Without JavaScript, search and the native sidebar filters submit through one GET form, and the form exposes an explicit Apply filters button. Source, language, group, and tag filters are hidden because their token-selection workflows require JavaScript.
- Filter lists contain at most 1,000 current user-visible options per list, ordered by name (normalized value for languages). Core applies the limit in SQL after visibility filtering. Tags start from distinct non-report names in `NewsItemTagCluster`, then probe indexed tag occurrences for a non-report tag on an ACL/TLP-visible story. Deduplicate candidates before these checks; `OFFSET 0` keeps PostgreSQL from expanding the probes into a full tag-table join. Core builds lists on request; frontend caches per user. Writes affecting those options must invalidate the relevant frontend scope. Chat's reference catalog omits options beyond this cap; direct Assess filters still accept them.
- Assess tag suggestions use `/api/assess/taglist` directly, independently of the filter-list cap/cache. Search matches literal substrings case-insensitively after trimming whitespace. Rank exact names first, then distinct ACL/TLP-visible story counts descending, then case-insensitive name and original name for stable ties; apply pagination afterward (20 suggestions by default). Combine occurrences across tag types, exclude types with a literal `report_` prefix (case-insensitive), and count each story once. Types such as `reporting` remain eligible. Frontend forwards the search as an encoded query parameter.
- Tag suggestions return `{name, story_count}` using the ranking aggregate across all visible stories, independently of sidebar filters. Truncate names with full-name titles and visible counts; Assess E2E covers long names/URLs.
- The remote token control's HTMX request guard reads `this.value`; HTMX inline handlers cannot call Alpine component methods such as `hasQuery()` directly. The Assess browser workflow covers searching and selecting a tag.
- Assess, Chat, and source/group references share `FilterData`, limited to ACL/TLP-visible stories. Sources/groups without visible stories are omitted; reference ACLs still apply.
- Story filters use existence checks for source/language membership, tags, reports, and attributes so matching related rows do not multiply stories. Source/group alternatives and language constraints must match the same news item. ACL and TLP checks remain on the filtered story query.
- Bulk updates own one transaction: missing, forbidden, or failed stories roll back every change and revision. Model `Story.apply_update` does not commit; the single-update wrapper retains its commit. Scheduling, cache invalidation, and realtime publication run only after the bulk commit. Error responses preserve the visible list and selection.
- Keep stable `assessSelection` in `assess-navigation.js`: changing inline `x-data` during HTMX settling can double-initialize scopes. Refresh metadata through card initialization/local swaps. Pagination replaces list/pagination; filter chips also replace the sidebar OOB.
- `/assess/display` saves compact/highlight/bookmark-bar preferences, updates current-user context, and preserves filters/selection. Invalid values use the shared 400 formatter. Explicit local 400 notification targets override body validation swaps; failures retain the list. Keep active custom dates/advanced criteria expanded.
- Paged user lists select ordered story IDs before loading story content and enriching votes/report counts. Every sort ends with the story ID as a stable tie-breaker. Counters project only ID/read/important, remove ordering/paging, and aggregate the filtered set once; `in_reports_count` retains its report-association count semantics.
- Story views reuse filter lists by user within the current request even with `CACHE_ENABLED=false`. This includes repeated detail/form context construction; subsequent requests still fetch fresh lists when the frontend cache is disabled.
- Upstream list failures return static 502: notification-only for HTMX, page-with-error for native navigation. Action 5xx and Delete/Ungroup 400/4xx/5xx target notifications, preserving lists/selection and Core statuses. Suppress failed sidebar history pushes; failed Any time restores controls from the current URL. Return only the load error, even after action success: HTMX selects the first notification bar.
- Story/report writes also invalidate news-item, bookmark, and filter caches. Admin ACL/role/source/group/settings writes invalidate all frontend caches.
- Bulk story updates reject non-string story IDs with a static 400 before looking up or updating any story. API coverage is in `test_assess_api.py`.
- Sidebar submissions, profile defaults, and dashboard shortcuts share canonical query parameters; source/group/language/tag values remain list-shaped. Saving an existing filter name updates it; identical criteria under a different name are rejected after canonical validation and serialization, including case normalization of choice fields.
- Saved-filter management creates, applies, defaults, and deletes searches. Sort help distinguishes publication-derived date from update time; relevance uses score, with full-text rank taking precedence.
- List refreshes after non-GET actions restore the active query from `HX-Current-URL`, including DELETE story actions. Deleting the last matching story leaves the filtered result empty; it must not show unfiltered stories while the sidebar still displays active filters.
- Cards retain/highlight active tag-name/type matches when collapsed or compact. Mutation replacements recover tags from Assess `HX-Current-URL`, including PUT. Expansion stays local; details show all tags. Coverage: Assess E2E and story view tests.
- Source icons on story cards add that source through a native Assess link, preserving repeated filter values and existing sources while clearing pagination. Assess list GETs use the requested filters, since `HX-Current-URL` still describes the previous search during an HTMX filter change. Card replacements and detail returns retain the Assess filter context.
- Dashboard shortcuts reuse saved-filter normalization, delete routes, and Assess URLs. Show the first three by default, with the rest behind Show more.
- Omnisearch fetches filter lists lazily, only for value resolution/suggestions.
- Paged navigation replaces `#story-list` and out-of-band `#story-pagination`, scrolls to the top, and keeps the sticky top bar mounted. Errors notify without replacing/appending stories. Stable search-input IDs preserve focus.
- Story Open/Edit and the selection shortcut carry a relative `assess_url` through editor layouts, saves, and card replacements. Explicit return URLs take precedence over `HX-Current-URL`, which stays on the initial page during infinite scroll. Back to Assess restores filters and pagination with a native link; only the application's Assess path is accepted. Direct story links fall back to ordinary Assess, and bookmark returns keep their existing destination.
- Selection Edit captures the component root at initialization; Alpine `$el` in handlers is the triggering button. Assess E2E exercises Shift+E, toolbar Edit, and return search without stubbing navigation.
- Assess remembers the latest search in user- and application-path-scoped localStorage. Opening bare Assess offers Restore last search or Dismiss; explicit filters, saved defaults, and reset links take precedence. Pagination updates the stored URL. Storage failures do not affect native return navigation.
- Infinite-scroll searches opened past the first page explain their starting result and offer Start from beginning with the same filters. Counts label the stories actually loaded; the footer range includes all appended batches and End of results does not imply earlier results were loaded.
- `Shift+Space` prevents native page-up on keydown and performs read/unread on keyup only with a selection. Bookmark detail shares this behavior and the [global shortcut/selection rules](frontend-development.md).
- Successful clustering selects the first submitted story before swapping, removing merged IDs. Failure preserves selection/dialog. `test_e2e_user.py::test_user_assess` performs two merges from three cards and checks survivors.
- Assess/bookmark toolbar action positions stay stable across selection counts; wrap counts/actions to keep Clear selection reachable and show the single-story cluster hint only when space permits.
- The Assess pagination/editing browser workflow reads the stored source ID from its seeded story and filters to that source so scheduled collection from other sources cannot change its expected total.
- Browser tests use `_get_assess_story_counts` to wait for both Alpine counts; wrapper visibility is insufficient.
- Search debounces 300 ms; blur does not resubmit. Sidebar filters/pagination share a replacement queue that cancels older requests. Browser tests wait for input requests, not blur. The Assess workflow’s display-save 400 verifies recovery; allow its expected console error only for that endpoint/workflow.
- `AssessSearchFilters` owns filter validation and serialization for Core, saved filters, and Chat; paging/internal controls stay separate. Chat links use canonical `/assess` queries with doseq encoding.
- Before `Story.get_by_filter(filter_args, current_user)`, Core validates model-proposed source, group, tag, language, and recent-story references against the user's visible catalog. Chat must never bypass this validation or turn proposed filters into raw SQL.

Relative date windows and explicit `timefrom` use the publication-derived story `created` date. Collection changes mark stories unread but do not force old stories into the current Shift window. See [Collection Updates](fuzzy-deduplication.md).

Preserve canonical and saved `last<N>` ranges. UTC starts: `shift` today midnight, `week` Monday, `month` first day, legacy `day` yesterday. `24h`/`last<N>` roll back from now. Custom bounds are additive: `timefrom` uses creation, `timeto` update. Any time removes preset/both bounds only; custom-only filters show a disabled placeholder, never a UI-only Core value. Coverage: `test_time_period_boundaries`.

## Entry Points

- Core: `src/core/core/api/assess.py`, `src/core/core/model/filter_data.py`, `src/core/core/service/cache_invalidation.py`
- Contract: `src/models/models/assess.py`
- Frontend: `src/frontend/frontend/views/story_views.py` (`get_filter_lists`), `src/frontend/frontend/views/dashboard_views.py`, `src/frontend/frontend/omnisearch.py`
- Templates: `src/frontend/frontend/templates/assess/sidebar/`, `src/frontend/frontend/templates/assess/saved_filter_cards.html`
- Return navigation and browser search storage: `StoryView._get_assess_return_url`, `src/frontend/frontend/static/js/assess-navigation.js`, `src/frontend/frontend/templates/assess/back_link.html`
- Chat: `src/core/core/service/chat.py`, `src/frontend/frontend/views/chat_views.py`

## Coverage

`src/core/tests/application/user_workspace/assessment/test_story_filters.py`; `src/frontend/tests/unit/views/test_story_view.py`; `src/frontend/tests/unit/test_omnisearch.py`; `src/frontend/tests/playwright/test_main_js.py`; pagination in `test_user_profile` in `src/frontend/tests/playwright/test_e2e_user.py`.

Recording `test_assess` marks two representative unread/unimportant stories read then important without fixed seed counts. Detailed filters, bulk actions, clustering, and editing belong in `test_e2e_user.py`.

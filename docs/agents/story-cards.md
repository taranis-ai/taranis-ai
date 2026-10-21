# Story Cards

## When To Load

Assess or bookmark story-card metadata, source icons, or frontend story enrichment.

## Contracts

- Source icons are served by an authenticated, user-catalog-scoped route with private ETag revalidation; icons are not repeated as base64 in every card. Missing/invisible sources return 404.
- Collapsed list cards fetch their detail area and secondary actions only when opened; failures keep the card and allow retry. Detail pages retain server-rendered content. Common triage actions remain visible; Edit and secondary operations live under More on list cards.
- Story cards show up to five distinct sources as icons, with each name in the shared styled tooltip and accessible label. Each icon is a Tab stop inside its tooltip wrapper, activating the shared tooltip's descendant-focus styling. Sources without an image use a newspaper icon with the same tooltip; sources absent from the user-visible filter catalog are omitted.
- With at most five news items, sources retain their first appearance order without frequency ranking. With more than five items, rank by news-item count and keep the first five sources; ties retain first appearance order.
- Enrichment uses the already-loaded source catalog for both lists and detail views. `source_infos` is frontend-only story metadata; summary fallback remains the first news item's content.

## Entry Points and Coverage

`src/frontend/frontend/views/story_views.py` (`_enhance_story_with_details`) and `src/frontend/frontend/templates/assess/story_card.html` share rendering across Assess, bookmarks, detail views, and action responses.

`test_story_card_shows_distinct_top_source_icons` in `src/frontend/tests/unit/views/test_story_view.py` covers rendering, deduplication, ranking, ties, the five-item boundary, and missing sources/icons through the story route.
The existing `test_user_assess` browser workflow verifies Tab navigation and the tooltip's computed visibility on keyboard focus.

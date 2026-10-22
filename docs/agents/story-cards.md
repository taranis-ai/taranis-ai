# Story Cards

Load for: Assess or bookmark story-card metadata, source icons, or frontend story enrichment.

## Contracts

- Source icons are served by an authenticated, user-catalog-scoped route with private ETag revalidation; icons are not repeated as base64 in every card. Missing/invisible sources return 404.
- Unread, Important, and In Reports remain visible in compact cards; read stories have no read-status badge.
- Unread cards use the primary border color; selection takes precedence with the info border color and matching background tint. Deselecting restores the unread or read border, including after card replacements.
- Compact cards use one-line summaries and accessible icon actions, beside content at 48rem or wider and below otherwise. Publication date stays in the tooltip; relevance belongs to regular cards.
- Regular cards use three columns at 80rem (metadata/content/actions); narrower cards keep metadata beside content and actions in one full-width row. Never stack to one column. Tags span metadata/content; sources and status occupy separate rows. Equal-width outline actions must survive OOB swaps and shrink/wrap labels without adding action rows.
- Collapsed regular cards show ten tags at the wide breakpoint and five below it. Active filter matches remain visible beyond those limits; the expansion count reflects the current layout. Compact cards retain the five-tag limit.
- Collapsed list cards fetch their detail area and secondary actions only when opened; failed or missing lookups return a static HTTP 502 notification, keeping the card and allowing retry. Detail pages retain server-rendered content. Common triage actions remain visible; Edit and secondary operations live under More on list cards. Regular cards in the wide three-column layout also show Edit Story and Version History below Important/Add to report, retaining edit permissions and showing history only when revisions exist. Lazy Delete targets the current Assess list, bookmark collection, or detail card through the shared story-action target helper.
- Expanded lists and full news-item cards share the `news_item_metadata` macro: source name, item-level Published/Collected timestamps, author, language, manual-entry indicator, and TLP when available. Language uses an outline pill in the bottom metadata row. Resolve source names by item source ID from the user-visible catalog before limiting story icons to five; fall back to the item's escaped source text when absent from that catalog. Manual-entry detection uses `osint_source_id`, independently of the free-text source description. Lazy details and tag-update fragments must also enrich the story. Omit missing values and use the shared datetime formatter; never substitute the story date for an item's missing publication date.
- Regular cards show the full primary URL below the title, visually ellipsized with the complete URL in its tooltip.
- Malformed story links leave the source-domain hint empty rather than failing list/detail rendering.
- Story cards show up to five distinct sources as icons, with each name in the shared styled tooltip and accessible label. Each icon is a native link and Tab stop inside its tooltip wrapper. Clicking it adds the source to the current Assess filters without duplicates, preserves other filter values, and resets pagination. Detail/bookmark cards link back to Assess, using the Assess return context when available. Sources without an image use a newspaper icon with the same tooltip; sources absent from the user-visible filter catalog are omitted.
- With at most five news items, sources retain their first appearance order without frequency ranking. With more than five items, rank by news-item count and keep the first five sources; ties retain first appearance order.
- Enrichment uses the shared source catalog for both lists and detail views. `source_infos` and `source_names` are frontend-only story metadata; summary fallback remains the first news item's content.

## Code and Tests

`src/frontend/frontend/views/story_views.py` (`_enhance_story_with_details`) and `src/frontend/frontend/templates/assess/story_card.html` share rendering across Assess, bookmarks, detail views, and action responses.

`test_story_card_shows_distinct_top_source_icons` in `src/frontend/tests/unit/views/test_story_view.py` covers rendering, deduplication, ranking, ties, the five-item boundary, and missing sources/icons through the story route.
The `test_user_assess` browser workflow verifies Tab navigation and the tooltip's computed visibility on keyboard focus.

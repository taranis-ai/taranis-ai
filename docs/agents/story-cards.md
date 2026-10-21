# Story Cards

## When To Load

Assess or bookmark story-card metadata, source icons, or frontend story enrichment.

## Contracts

- Source icons are served by an authenticated, user-catalog-scoped route with private ETag revalidation; icons are not repeated as base64 in every card. Missing/invisible sources return 404.
- Unread, Important, and In Reports remain visible in compact cards; read stories have no read-status badge.
- Compact cards use an inline metadata row, a headline with an external-link icon, a one-line summary, and icon-only actions with accessible names and tooltips. Actions sit beside the content when the card is at least 48rem wide and below it otherwise. The latest publication date remains in the date tooltip; relevance stays in the regular layout.
- Regular cards have exactly two layouts, based on card width: at 80rem and above, metadata, story content, and grouped actions sit side by side; below that, metadata stays beside the content and all actions occupy one row spanning the full card width. Tags start at the left edge and span the metadata and content columns. Cards never stack into one column. The metadata column shrinks on narrower cards, and sources and status badges retain separate rows for consistent scanning. Action buttons share equal widths and outline styling, including after bookmark OOB replacements and state-label changes; on narrow cards they shrink together and labels can wrap without moving buttons to another row.
- Collapsed list cards fetch their detail area and secondary actions only when opened; failures keep the card and allow retry. Detail pages retain server-rendered content. Common triage actions remain visible; Edit and secondary operations live under More on list cards.
- Expanded lists and full news-item cards share the `news_item_metadata` macro: source name, item-level Published/Collected timestamps, author, manual-entry indicator, and TLP when available. Resolve source names by item source ID from the user-visible catalog before limiting story icons to five; fall back to the item's escaped source text when absent from that catalog. Manual-entry detection uses `osint_source_id`, independently of the free-text source description. Lazy details and tag-update fragments must also enrich the story. Omit missing values and use the shared datetime formatter; never substitute the story date for an item's missing publication date.
- In regular cards, the primary article link occupies its own row below the title and displays the full URL, with visual ellipsis when it exceeds the content width; its tooltip retains the complete URL.
- Malformed story links leave the source-domain hint empty rather than failing list/detail rendering.
- Story cards show up to five distinct sources as icons, with each name in the shared styled tooltip and accessible label. Each icon is a Tab stop inside its tooltip wrapper, activating the shared tooltip's descendant-focus styling. Sources without an image use a newspaper icon with the same tooltip; sources absent from the user-visible filter catalog are omitted.
- With at most five news items, sources retain their first appearance order without frequency ranking. With more than five items, rank by news-item count and keep the first five sources; ties retain first appearance order.
- Enrichment uses the shared source catalog for both lists and detail views. `source_infos` and `source_names` are frontend-only story metadata; summary fallback remains the first news item's content.

## Entry Points and Coverage

`src/frontend/frontend/views/story_views.py` (`_enhance_story_with_details`) and `src/frontend/frontend/templates/assess/story_card.html` share rendering across Assess, bookmarks, detail views, and action responses.

`test_story_card_shows_distinct_top_source_icons` in `src/frontend/tests/unit/views/test_story_view.py` covers rendering, deduplication, ranking, ties, the five-item boundary, and missing sources/icons through the story route.
The existing `test_user_assess` browser workflow verifies Tab navigation and the tooltip's computed visibility on keyboard focus.

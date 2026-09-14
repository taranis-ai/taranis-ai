# Fuzzy hashes: collection updates and story clustering

## Shared fingerprint, separate decisions

CTPH measures textual similarity, not semantic equivalence or the importance of a correction. Reuse fingerprints across collection and story clustering, with independent candidate scopes, thresholds, and actions.

## Use case 1: implemented collection behavior

Article identity is the URL within its OSINT source. Use the sanitized URL as stored; do not strip tracking parameters, fragments, or infer canonical URLs. Changed URLs therefore identify different items. A reused live-page URL represents successive versions of one item.

| Incoming item | Action |
| --- | --- |
| Known URL, unchanged normalized source fields | Skip without a revision |
| Known URL, changed content/title/author/language | Update the existing item; preserve before/after story revisions |
| Known URL, empty replacement body | Reject and preserve existing content |
| Older/equal collection delivery for a known item | Skip as stale |
| Different URL, strongest same-source score at least the grouping threshold | Keep both items in the same story |
| No qualifying match, tied strongest matches across stories, or ineligible target | Create a separate story |

The initial grouping threshold is 85, configurable through Core's `COLLECTION_GROUP_THRESHOLD`. The proposed 95-point discard band is deliberately not implemented: URL identity decides whether there is one article, and similarity cannot justify deleting a different article's evidence. Known URLs are updated even below 85 and for short bodies without fingerprints.

Story snapshots provide revision storage; the diff compares individual news-item fields. Story titles, summaries, review notes, tags, and membership are preserved by collection updates. Changed stories become unread and re-enter relative date windows. Affected story IDs reach post-collection bots; normal bot behavior and MISP scheduling apply. Analyst review queues already in progress remain fixed snapshots.

Implementation: `src/core/core/service/collection.py`, `src/core/core/model/news_item.py`, `src/models/models/revision_diff.py`, and the existing worker collection and post-collection bot pipeline. See [OSINT source collection](osint-sources.md#collection-updates-and-fuzzy-grouping) for operational details.

Limitations: detection depends on a fresh collection delivering the article; there is no independent article revisit job. Run timestamps prevent older overlapping deliveries, but cannot prove publisher version order. History remains attached to story lifetime, not an independent permanent article archive. Existing historic duplicate URLs are retained. Similarity thresholds still require evaluation against representative content, especially boilerplate-heavy RSS summaries.

## Use case 2: proposed cross-source story clustering

The existing Story Bot sends stories to an external NLP service and submits returned event clusters to Core. Fuzzy evidence can supplement it for copied, syndicated, or lightly rewritten coverage across sources.

Use an independent clustering threshold and bounded event window; do not inherit the collection threshold automatically. Start with evaluated suggestions before enabling automatic grouping. Keep each source item, link, attribution, and publication time, even at score 100.

A low fuzzy score must not veto a semantic match: independently written or translated reports can concern the same event. Conversely, shared boilerplate can give unrelated articles high scores. Preserve the semantic path for unmatched items, including short bodies without fingerprints.

Avoid unrestricted similarity chains: A matching B and B matching C does not establish that A and C belong together. Initially compare with a representative article and measure missed coverage before adding more complex clustering. Respect Core grouping restrictions and avoid repeatedly undoing analyst decisions.

Evaluate unchanged fetches, typo fixes, meaningful single-word/number corrections, large stable-URL updates, syndicated copies, unrelated boilerplate, short summaries, and independently written coverage. Measure lost meaningful updates separately from incorrect grouping. This cross-source extension remains unimplemented.

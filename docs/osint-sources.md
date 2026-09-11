# OSINT Source Collection Activity

Administrators can inspect recent collection activity on an OSINT source's detail page. The value appears next to the lifetime number of news items stored for that source.

Use the period control (**Day**, **Week**, **Month**) on the source's detail page to select:

- **Day**: the trailing 24 hours
- **Week**: the trailing 7 days, selected by default
- **Month**: the trailing 30 days

Changing the period does not change the lifetime total. Recent activity uses the time each news item was collected by Taranis, not the publication time supplied by the source.

## Fuzzy deduplication

Collection always skips near-identical article bodies from the same OSINT source collected in the preceding 30 days (UTC), using a CTPH score of at least 90. Exact title/URL hash deduplication runs first. Bodies shorter than 256 UTF-8 bytes use exact deduplication only. The body is normalized for Unicode and whitespace before hashing; titles and URLs do not affect the fuzzy fingerprint.

Fuzzy rejection applies to worker news-item ingestion. Manual-source items, explicit Assess creation, JSON imports, MISP/RT story synchronization, and conflict resolution retain their existing identity rules. A match skips the incoming item and preserves the existing story. Duplicate-only collector runs report `NOT_MODIFIED`.

The PostgreSQL migration automatically populates existing fingerprints without changing article timestamps or deleting duplicates. Content edits recompute fingerprints, which remain internal metadata. Migration time depends on the stored article volume.

CTPH scores measure textual similarity, not semantic equivalence: a small but meaningful correction can still score 100.

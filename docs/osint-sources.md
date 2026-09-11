# OSINT Source Collection Activity

Administrators can inspect recent collection activity on an OSINT source's detail page. The value appears next to the lifetime number of news items stored for that source.

Use the period control (**Day**, **Week**, **Month**) on the source's detail page to select:

- **Day**: the trailing 24 hours
- **Week**: the trailing 7 days, selected by default
- **Month**: the trailing 30 days

Changing the period does not change the lifetime total. Recent activity uses the time each news item was collected by Taranis, not the publication time supplied by the source.

## Fuzzy deduplication

Core can skip near-identical collected articles even when their titles or URLs differ. Exact title/URL hash deduplication still runs first. Fuzzy deduplication is opt-in and compares only articles from the same OSINT source collected during the trailing window, ending at the current UTC time. The source's display name and publication dates do not affect this window.

Set these environment variables on Core (the standard `docker/compose.yml` forwards them from `.env`):

| Variable | Default | Accepted values |
| --- | --- | --- |
| `FUZZY_DEDUP_ENABLED` | `false` | Boolean |
| `FUZZY_DEDUP_LOOKBACK_DAYS` | `30` | 1–365 days |
| `FUZZY_DEDUP_THRESHOLD` | `90` | CTPH score 1–100 |

The fingerprint uses ssdeep-compatible CTPH through `ppdeep`, on the sanitized article body after NFC Unicode and whitespace normalization. Bodies shorter than 256 UTF-8 bytes have no fingerprint and use exact deduplication only. Titles, links, tags, and review text are excluded. Scores are algorithm-specific similarity measurements, not percentages of matching words or a guarantee that an article is unchanged. Even a score of 100 can hide a changed number or other meaningful correction. Keep this feature disabled for sources where every revision must be retained, and evaluate sample articles before enabling it.

Fuzzy rejection applies to `/api/worker/news-items`. Manual-source items, missing sources that fall back to Manual, explicit Assess creation, JSON imports, MISP/RT story synchronization, and conflict resolution keep their existing identity rules. Every new persisted item receives a fingerprint when eligible, including items created while deduplication is disabled; content edits recompute it. Fingerprints are local metadata and are not exported or trusted from incoming payloads.

A fuzzy match skips the incoming item and preserves the existing item and story. Core logs the matched item ID, source ID, and score. A duplicate-only collector run retains the existing `NOT_MODIFIED` status. Existing duplicate records are never merged or deleted by this feature.

### Existing items and activation

The normal PostgreSQL startup migration adds a nullable column and a source/collection-time index. It does not calculate historical fingerprints. After upgrading Core with fuzzy rejection disabled, fill missing fingerprints from the configured window:

```bash
docker compose -f docker/compose.yml exec core taranis-cli backfill-fuzzy-hashes
# Or inside a Kubernetes core pod:
kubectl exec deploy/core -- taranis-cli backfill-fuzzy-hashes
```

The command accepts `--days 60` and `--batch-size 500`. It commits each batch and can be rerun after interruption; existing fingerprints are left intact. It reports scanned, filled, and short/empty-body counts. Short bodies remain NULL and are counted again on reruns. Backfill preserves content, story membership, and collected/published/updated timestamps. Run it again before enabling a larger lookback window if that older data has never been fingerprinted. Until backfill completes, older NULL fingerprints do not participate in comparison.

Enable `FUZZY_DEDUP_ENABLED=true`, restart Core, and verify collection against a representative source. PostgreSQL serializes fuzzy check and insertion per source; comparisons stream fingerprints from that source's window. High-volume sources or long windows increase collection latency. SQLite development databases do not provide PostgreSQL row-lock guarantees, and the repository's migration runner only upgrades PostgreSQL; use a fresh SQLite development database or manually add the nullable `fuzzy_hash TEXT` column and `(osint_source_id, collected)` index to an existing one.

Disable the setting and restart Core to restore exact-only ingestion. Application rollback can leave the unused column and index in place. Disabling or rolling back cannot recover previously skipped incoming articles; recollect them from their source if needed.

# Core ORM Profiling Findings

This report records the first full canonical synthetic baseline for issue #1105.
It provides reproducible evidence for review before selecting application
optimizations. The findings identify candidates to investigate; they do not
establish production latency or a performance target.

## Run and protocol

| Item | Value |
|---|---|
| Run ID | `20261030t112719z-3239826` |
| Source revision | `f299cd49fc4203939431236d24f22a4894c81095` |
| Application baseline | `f4bbd661f11ae7b491be3383dc90924c002e65bf` |
| Database | PostgreSQL 18.6; `pg_stat_statements`; isolated Compose stack |
| PostgreSQL image | `postgres:18-alpine@sha256:77f585114c32fbca283dc835b0596f4e52b51b4c6662d7810b2f4084f60a1873` |
| Synthetic profiles | Empty, single, normal, stress roots, stress children |
| Timing protocol | Five warmups plus 30 single-invocation rounds for each included scenario/profile |
| Python and memory profiling | cProfile and Memray in separate passes |
| Snapshot | No sanitized production snapshot or production aggregates supplied |
| Source verification | Passed for the measured run |

The profiles use 0, 1, or 20 story roots for empty, single, and normal data;
stress roots uses 200 roots; stress children keeps 20 roots and raises each
root's child count from 3 to 30. The frozen manifest also fixes tags,
attributes, payload sizes, and revisions. The batch scenarios use sizes 1, 10,
100, and 1,000.

| Profile | Scenario/profile pairs | Measured rounds |
|---|---:|---:|
| Empty | 215 | 6,450 |
| Single | 359 | 10,770 |
| Normal | 545 | 16,350 |
| Stress roots | 359 | 10,770 |
| Stress children | 359 | 10,770 |
| **Total** | **1,837** | **55,110** |

The timing pass recorded no failed scenarios. Its 144 skips are cases that do
not apply to the selected dataset profile. Attribution completed for the same
profile matrix. Memray ran on the selected serialization and collection paths;
the matched control pass completed for the selected control scenarios.

Raw, gitignored artifacts occupy approximately 1.7 GB locally. They include
native pytest-benchmark output, event samples, `pg_stat_statements` deltas,
cProfile and Memray files, plans, manifests, source hashes, and checksums:

- [Generated aggregate report](../../.orm-artifacts/20261030t112719z-3239826/report.json)
- [Native artifact checksums](../../.orm-artifacts/20261030t112719z-3239826/checksums.json)
- [Captured environment and database settings](../../.orm-artifacts/20261030t112719z-3239826/environment.json)
- [Captured scenario specifications](../../.orm-artifacts/20261030t112719z-3239826/specifications.json)

Regenerate the aggregate report with:

```sh
UV_CACHE_DIR=/tmp/uv-cache ./dev/profile_orm.sh report \
  --output "$PWD/.orm-artifacts/20261030t112719z-3239826"
```

## Inventory coverage

| Inventory | Measured | Excluded with evidence | Pending | Total |
|---|---:|---:|---:|---:|
| Route/method entries | 498 | 494 | 2 | 994 |
| ORM methods, serializers, and relationships | 667 | 0 | 204 | 871 |
| CLI, housekeeping, and startup entrypoints | 5 | 0 | 0 | 5 |

The generated report remains incomplete because of the pending inventory rows.
The two pending routes are batch workflows:

| Route | Evidence collected | Why the generated status is pending |
|---|---|---|
| `POST /api/worker/news-items` | Batch sizes 1, 10, 100, and 1,000 each have 30 normal-profile rounds. | The coverage rule also requires stress-root and stress-child profiles, which batch cases do not use. |
| `PUT /api/worker/word-list/<string:word_list_id>` | Batch sizes 1, 10, 100, and 1,000 each have 30 normal-profile rounds. | The coverage rule also requires stress-root and stress-child profiles, which batch cases do not use. |

The measurements exist for both routes, but the generated coverage status does
not yet recognize the plan's normal-profile-only batch cases as complete. This
classification should be corrected before treating route inventory coverage as
closed.

The 204 pending ORM declarations are not yet reconciled to scenarios or
source-backed exclusions. The largest pending groups are:

| Declaration source | Pending declarations |
|---|---:|
| `core.model.osint_source` | 25 |
| `core.model.story` | 24 |
| `core.model.word_list` | 19 |
| `core.model.report_item` | 14 |
| `core.model.attribute` | 13 |
| `core.model.asset` | 12 |
| `core.model.news_item` | 11 |
| `core.model.report_item_type` | 11 |

These declarations need reachability review. A pending declaration is not proof
that a production path is unmeasured; it means the inventory has not yet linked
it to a completed scenario or justified its exclusion.

## Measured latency and database activity

Times below are medians over the canonical rounds. p95 is reported to show
sample spread. SQL statement and relationship counts are scenario medians.
PostgreSQL time is the summed server execution time for the scenario's
normalized statements, not the whole request time.

| Scenario/profile | Wall median | p95 | SQL statements | Relationship loads | Cursor time | PostgreSQL time | Response bytes |
|---|---:|---:|---:|---:|---:|---:|---:|
| `assess.stories` / normal | 42.4 ms | 45.0 ms | 23 | 8 | 13.9 ms | 2.2 ms | 313 KB |
| `assess.stories` / stress roots | 220.8 ms | 468.5 ms | 25 | 10 | 61.7 ms | 31.9 ms | 3.14 MB |
| `assess.stories` / stress children | 152.0 ms | 404.8 ms | 25 | 10 | 28.2 ms | 8.6 ms | 2.99 MB |
| `worker.stories` / normal | 100.8 ms | 104.1 ms | 212 | 210 | 34.8 ms | 6.1 ms | 327 KB |
| `worker.stories` / stress roots | 934.5 ms | 1,181.3 ms | 2,012 | 2,010 | 299.4 ms | 46.9 ms | 3.13 MB |
| `worker.stories` / stress children | 634.9 ms | 896.2 ms | 1,346 | 1,344 | 197.5 ms | 28.3 ms | 3.12 MB |
| `assess.story-group` / normal | 70.3 ms | 78.4 ms | 66 | 25 | 36.5 ms | 14.3 ms | 88 B |
| `assess.story-group` / stress children | 823.9 ms | 864.8 ms | 282 | 133 | 713.1 ms | 648.0 ms | 88 B |
| `config.template-list` / normal | 85.5 ms | 89.2 ms | 4 | 2 | 1.2 ms | 0.09 ms | 112 KB |

### Supported batch sizes

| Batch | Median latency | p95 | Statements | Flushes | Commits | PostgreSQL time |
|---:|---:|---:|---:|---:|---:|---:|
| News-item ingest: 1 | 40.2 ms | 52.0 ms | 27 | 7 | 1 | 4.3 ms |
| News-item ingest: 10 | 187.1 ms | 196.8 ms | 270 | 70 | 10 | 14.4 ms |
| News-item ingest: 100 | 1.62 s | 1.73 s | 2,700 | 700 | 100 | 125.3 ms |
| News-item ingest: 1,000 | 17.90 s | 18.82 s | 27,000 | 7,000 | 1,000 | 3.10 s |
| Word-list replace: 1 | 16.1 ms | 21.3 ms | 5 | 1 | 1 | 0.30 ms |
| Word-list replace: 10 | 14.9 ms | 21.1 ms | 5 | 1 | 1 | 0.52 ms |
| Word-list replace: 100 | 18.7 ms | 25.9 ms | 5 | 1 | 1 | 1.13 ms |
| Word-list replace: 1,000 | 62.2 ms | 73.9 ms | 5 | 1 | 1 | 7.64 ms |

## What looks worth investigating

These are candidates for the Phase 3 review, not approved changes.

1. **News-item ingestion repeats database work per item.** The 1,000-item
   scenario takes 17.9 seconds and records 27,000 statements, 7,000 flushes,
   and 1,000 commits. cProfile attributes most of the route time to
   `CollectionService.ingest_item`, `_create_item`, and `_record_change`, with
   repeated SQLAlchemy execution beneath them. The word-list replacement path
   stays at five statements and one flush/commit even at 1,000 entries, making
   it a useful comparison. Review whether the ingest transaction and change
   recording boundaries are required per item before proposing a batch change.

2. **The worker story response triggers many lazy loads.** For 20 normal roots,
   `worker.stories` records 210 relationship loads. With 200 roots it records
   2,010; the 30-child fan-out profile records 1,344. The cProfile trace for
   stress roots shows 2,010 SQLAlchemy lazy-load emissions from
   `Story.to_worker_dict`. This directly links the latency increase to per-story
   relationship loading and makes the loading strategy a strong review
   candidate. The response also grows to about 3.1 MB in the stress profiles.

3. **Story grouping becomes database-bound at high child fan-out.** The
   `assess.story-group` stress-children median is 823.9 ms, of which PostgreSQL
   reports 648.0 ms; the request executes 282 statements. The captured plan for
   the slowest individual statement is only about 6.5 ms, which points toward
   accumulated query count rather than one single long statement. Review the
   per-story queries in `StoryService.group_stories` and its model call path.

4. **Assess story listing grows with returned data.** `assess.stories` moves
   from 42.4 ms for the normal 20-root profile to 220.8 ms for 200 roots, with
   a response of about 3.14 MB. Stress-root server execution is 31.9 ms and the
   largest captured plan is a sort taking about 9.5 ms. Review query results,
   hydration, and serialization together before deciding which part is
   material.

5. **Template-list latency is not explained by SQL execution.** The normal
   template-list result is 112 KB, but its four statements total about 0.09 ms
   of PostgreSQL execution. If this endpoint matters to users, profile file
   access, template parsing, and response serialization before changing ORM
   queries.

The matched instrumentation controls showed about 3.4% overhead for normal
`assess.stories`, 9.6% for stress roots, and 6.4% for stress children. Other
controls varied by scenario and profile; the comparison table is in the raw
report. cProfile and Memray runs are diagnostic and are not canonical latency
samples.

No finding here establishes a production bottleneck. The normal dataset is
synthetic, and the production snapshot is absent. Review plans and native
profiles alongside these aggregates, then decide together which candidates to
change and measure again.

## Exclusions

The route inventory contains 494 documented exclusions. They do not count as
measured ORM workflows because they are automatic framework methods, cannot
reach their handler, or do not perform Core database work.

| Exclusion reason | Entries | Treatment |
|---|---:|---|
| Flask-generated `HEAD` and `OPTIONS` | 484 | Accounted for by their registered route; generated automatically by Flask. |
| Registered path omits a required handler argument | 4 | Excluded because Flask dispatch fails before ORM access. |
| Process-local conflict state | 2 | Excluded because the operations only read or clear in-memory conflict dictionaries. |
| Direct file serving | 3 | Excluded because the handlers serve packaged or static files without Core persistence. |
| Separate Worker required | 1 | Excluded because successful processing waits for a Worker absent from the isolated Core stack and Core itself does not persist data on this route. |
| **Total** | **494** | |

The ten non-automatic exclusions are listed individually:

| Route | Evidence-based reason |
|---|---|
| `PUT /api/bots` | The collection URL omits `bot_id`; Flask raises `TypeError` before the handler or ORM runs. |
| `PUT /api/connectors/conflicts/stories` | The URL omits `story_id`; dispatch fails before the handler. |
| `PUT /api/worker/bots` | The collection URL omits `bot_id`; dispatch fails before the handler or ORM runs. |
| `PUT /api/worker/word-lists` | The collection URL omits `word_list_id`; dispatch fails before the handler or ORM runs. |
| `GET /api/connectors/conflicts/stories/<string:story_id>` | Reads process-local conflict data; the existing-conflict database-resolution branch is exercised by its scenario. |
| `POST /api/connectors/conflicts/clear` | Clears process-local conflict dictionaries only. |
| `GET /api/static/default_word_lists.json` | Serves a packaged JSON file directly. |
| `GET /api/static/openapi3_1.yaml` | Serves a packaged OpenAPI file directly. |
| `GET /static/<path:filename>` | Flask's static handler serves files without entering Core persistence. |
| `POST /api/assess/news-items/fetch` | Successful processing waits on the separate simple-web-collector Worker; the Core endpoint persists no data itself. |

The checked-in [exclusion registry](../../src/core/tests/performance/orm/baseline/exclusions-v1.json)
contains source references for each explicit exclusion. It also documents why
the default Flask static route and the process-local conflict handlers do not
reach the ORM.

## Existing PostgreSQL correctness failures

The separate correctness run found three existing failures on the base
application: product-type search applies `ILIKE` to a PostgreSQL enum, and
schema-generated bookmark quick-save and membership requests attempt to persist
a NUL character as a story ID. These are recorded in the correctness artifacts
and are not performance changes.

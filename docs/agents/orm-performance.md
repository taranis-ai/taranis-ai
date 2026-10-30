# Core ORM Performance Workflow

This workflow profiles Core's production entrypoints against an isolated,
disposable PostgreSQL 18 database. It is for collecting evidence before an
optimization is chosen. The raw run directory is local and gitignored; only
scenario contracts, dataset metadata, and reviewed findings belong in Git.

## Start a run

From the repository root, install the optional profiling tools in the Core
environment with `uv sync --directory src/core --extra dev --extra performance
--frozen`. The Compose runner builds Core from the checked-out source, then
starts a private PostgreSQL, Redis, and Core stack. PostgreSQL and Redis images,
versions, and database settings are pinned in `dev/orm/compose.yml`. The runner
destroys that project and its volumes when the operation exits.

Use the manual runner for these operations:

```sh
./dev/profile_orm.sh inventory
./dev/profile_orm.sh pilot --profile single --path assess
./dev/profile_orm.sh baseline
./dev/profile_orm.sh report --output .orm-artifacts/<run-id>
./dev/profile_orm.sh correctness
```

`inventory` captures routes and methods, authorization hooks, mapped models,
relationships, CLI commands, housekeeping jobs, startup SQL, and source
declarations. The database-free registry check fingerprints declarations,
route registrations, and mapped relationships so changed source must be
reviewed and reclassified. `pilot` uses one warmup and two measured calls
to validate scenario inputs and dataset shape. Review pilot outcomes and
non-sensitive production aggregates before changing `baseline/manifest-v1.json`
from `pilot-required` to `frozen`. `baseline` uses the manifest's five warmups
and thirty single-invocation rounds for timing, then runs separate cProfile,
Memray, and instrumentation-control passes. The report stays incomplete while
any reachable route, transaction boundary, or mapped-model operation lacks
measured scenarios or a source-backed exclusion.

The runner accepts `--profile`, comma-separated `--path` substrings, and
`--pass` to narrow a diagnostic run. Profiles are `empty`, `single`, `normal`, `stress_roots`, and
`stress_children`; passes are `timing`, `python`, `attribution`, `allocation`,
and `control`. Keep diagnostic runs separate from canonical timing. pytest
benchmark JSON, scoped SQLAlchemy events, PostgreSQL statistics, cProfile
files, Memray reports, plans, manifests, source hashes, and checksums are kept
under `.orm-artifacts/<run-id>`.

## Datasets and scenarios

Synthetic identifiers and timestamps are deterministic. The root-count and
relationship-fan-out stress profiles vary independently. Paginated collection
scenarios request all fixture roots within the application's documented page
limit. Batch scenarios exercise ingestion and word-list replacement at sizes
1, 10, 100, and 1,000. Each write warmup and measurement restores the same
prepared database template outside its timed call. Each invocation starts with
a fresh SQLAlchemy session and an empty profiling Redis database.

Scenarios call the real Flask routes, CLI commands, serializers, and startup
factory. External transports are substituted only at their HTTP boundary; Core
models, sessions, commits, and persistence stay real. A scenario with a required
identity is skipped when the selected dataset cannot provide it. Denied,
invalid, no-result, rollback, and batch inputs have separate scenario IDs so
they cannot stand in for a successful workflow.

A production snapshot is optional and must be supplied as a sanitized custom
format PostgreSQL archive (`pg_dump -Fc`) with a separate JSON manifest. Set
`ORM_SNAPSHOT` to the archive and `ORM_SNAPSHOT_MANIFEST` to that manifest when
running the script. The manifest must include the source revision, PostgreSQL
18 version, schema state, capture date, sanitization steps and changes,
SHA-256, local scenario identities, and local admin/user names. It must state
`"sanitized": true`. The runner verifies the checksum before restoring it.
Never put the archive or sensitive manifest in Git. Reports explicitly say
when no production snapshot was supplied and keep synthetic results separate.

## Reading evidence

pytest-benchmark is the source for canonical latency samples. SQLAlchemy event
records measure cursor time, statement fingerprints, relationship/column loads,
flushes, transaction starts, commits, rollbacks, and failures. PostgreSQL
statistics provide normalized query text and query IDs within that run, server
execution time, rows, buffers, and WAL. cProfile identifies Python hydration
and serializer costs; Memray runs independently for serialization and paged
large-result allocation. Read plans use `EXPLAIN (ANALYZE, BUFFERS, FORMAT
JSON)` outside the timed samples. Matched timing and uninstrumented control
scenarios report the observer overhead where both native benchmark results are
available.

Never compare PostgreSQL query IDs across restored databases or software
versions. Match evidence by stable scenario ID and normalized query structure.
An unavailable statistic remains unknown. Review `report.json` and native tool
outputs together; a successful HTTP status alone does not establish that all
ORM-reachable declarations were exercised.

The PostgreSQL correctness operation runs Core's ordinary correctness suite
with discovery instrumentation and keeps that evidence separate from
benchmarks. It records existing application failures without changing
application behavior to make the baseline pass.

## Current baseline state

No sanitized production snapshot or approved production aggregates have been
supplied. The synthetic manifest is frozen from the reviewed pilot cardinalities
in `baseline/manifest-v1.json`.

The first canonical slice is run `20261030t110327z-3199488` against the frozen
normal profile. `assess.stories` completed 30 measured rounds with a 43.5 ms
median and 49.7 ms p95; its matched uninstrumented control median was 42.2 ms.
The instrumented samples had a median of 23 SQL statements, 8 relationship
loads, 15.1 ms cursor execution time, and 2.33 ms of PostgreSQL execution time.
PostgreSQL reported no shared block reads. The response payload median was
313,422 bytes. The sample includes the Assess story query and eager relationship
loads for news items, attributes, tags, sources, roles, and user data.

cProfile and Memray outputs for this path are in the same local run directory;
they are diagnostic runs and are not comparable to canonical latency. Native
artifact checksums are in the run's `checksums.json`; raw artifacts remain
gitignored. The source-state check passed. This is a synthetic, single-path
result, not a production-wide baseline or an optimization recommendation. The
report still lists uncovered routes, methods, and entrypoints, so Phase 2 is
incomplete.

PostgreSQL correctness discovery on the base application found three existing
failures: product-type search applies `ILIKE` to a PostgreSQL enum, and the
schema-generated bookmark quick-save and membership requests attempt to persist
a NUL character as a story ID. Keep those results in the correctness artifacts
and do not turn them into profiling optimizations.

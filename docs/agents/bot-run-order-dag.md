# Bot Run Order DAG

## When To Load

Bot dependencies, `RUN_AFTER_COLLECTOR`, `RUN_AFTER_BOTS`, DAG previews, or post-collection scheduling.

## Contracts

- Bot creation requires an explicitly supplied `name`; `BotCreate` overrides the optional input default. Updates may omit it. Invalid create payloads return a static 400 error, covered by `TestBotConfigApi` in `test_config_api.py`.
- Nodes are configured `Bot.id` UUIDs, never bot types (multiple instances may share a type). `RUN_AFTER_COLLECTOR=true` defines roots; `RUN_AFTER_BOTS` stores comma-separated parent UUIDs edited through the run-order UI.
- Core validates dependencies, self-links, and cycles. Collector runs enqueue the reachable enabled DAG as one RQ job. Successful manual/cron standalone runs schedule one downstream pipeline for their `worker_id`; the pipeline inherits the trigger filter.
- A pipeline asks Core for the union of bot-selected stories in one response, then runs bots in dependency order over a shared in-memory context. Clustering moves news items in that context before later summary/enrichment stages. Bots return staged changes; their worker run submits one success result to `/api/tasks`.
- Core locks and compares the downloaded story revisions, applies all stages and the task result in one database transaction, and deduplicates successful retries by RQ run ID. A stale revision returns 409; invalid or failed stages leave no Core writes. Standalone bots use the same staged submission path. Post-commit cache, event, and MISP refreshes remain outside the transaction.
- Pipeline RQ timeout is `ceil(1.2 × sum(each bot's EXECUTION_TIMEOUT or RQ_DEFAULT_JOB_TIMEOUT))`. HTTP `REQUESTS_TIMEOUT` does not set the whole-bot timeout.
- Multi-parent nodes wait only for parents in the current chain. Missing/disabled parents do not block it, but previews warn about them.
- Dependency preview shows the edited bot's connected component. Collector Chain shows the full enabled collector order only for bots in that chain; disabled parents may still appear in dependency badges.
- Bot indexes are unique. Accept integers/integer strings, reject booleans/floats, treat null/empty as omitted, and preserve zero and omitted-update semantics. New forms suggest max+1; availability checks exclude the current bot. Database conflicts retain curated validation errors.
- Use one `POST /api/config/bots/dag-preview`, sending only candidate `id`, `type`, `index`, `enabled`, and the two dependency fields. Reject unrelated fields; malformed previews return a generic 400.
- Preview candidates validate only submitted scheduling parameters, so required execution settings do not block new or existing bot previews. Preview state is never persisted. Omitted run-order fields use their defaults; `RUN_AFTER_COLLECTOR` is a native boolean in list badges and forms.

## Entry Points and Coverage

`src/core/core/model/bot.py`, `src/core/core/managers/queue_manager.py`, `src/core/core/service/task.py`, `src/models/models/admin.py`, `src/worker/worker/bots/bot_tasks.py`, `src/frontend/frontend/views/admin_views/bot_views.py`.

Tests: `src/core/tests/application/admin_console/configuration/test_bot_dag.py`, `src/core/tests/application/worker_pipeline/test_bot_pipeline.py`, `src/core/tests/application/admin_console/configuration/test_queue_manager_scheduler_extended.py`, `src/frontend/tests/unit/views/test_bot_view.py`, `src/frontend/tests/playwright/test_e2e_admin.py`, `src/worker/tests/bots/test_bot_tasks.py`.

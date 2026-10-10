# Bot Run Order DAG

## When To Load

Bot dependencies, `RUN_AFTER_COLLECTOR`, `RUN_AFTER_BOTS`, DAG previews, or post-collection scheduling.

## Contracts

- Bot creation requires an explicitly supplied `name`; `BotCreate` overrides the optional input default. Updates may omit it. Invalid create payloads return a static 400 error, covered by `TestBotConfigApi` in `test_config_api.py`.
- Nodes are configured `Bot.id` UUIDs, never bot types (multiple instances may share a type). `RUN_AFTER_COLLECTOR=true` defines roots; `RUN_AFTER_BOTS` stores comma-separated parent UUIDs edited through the run-order UI.
- Core validates dependencies, self-links, and cycles. Collector runs enqueue the reachable enabled DAG as one RQ job. Successful manual/cron standalone runs schedule one downstream pipeline for their `worker_id`; the pipeline inherits the trigger filter.
- Post-collection scheduling requires explicit IDs of new or changed stories; an empty list queues nothing. Automatic runs apply each bot type's completion-attribute filter within that scope, bypassing publication-date windows and configured limits. Explicit manual story selections remain force runs. Collection clears completion attributes when content or membership changes, preserving them for unchanged or stale inputs.
- A pipeline asks Core for the union of bot-selected stories in one response, then runs bots in dependency order over a shared in-memory context. Clustering moves news items in that context before later summary/enrichment stages. Bots return staged changes; their worker run submits one success result to `/api/tasks`.
- Pipelines with OpenRouter batch stages checkpoint their configurations, story snapshot, context, completed stages, and current batch in private RQ metadata. Retries resume the pending stage without redownloading stories or repeating completed bots. No Core updates are submitted while a batch is pending; success clears the checkpoint. Redis restart loses it per [Redis Runtime State](redis-runtime-state.md).
- Core locks and compares the downloaded story revisions, applies all stages and the task result in one database transaction, and deduplicates successful retries by RQ run ID. A stale revision returns 409; invalid or failed stages leave no Core writes. Standalone bots use the same staged submission path. Post-commit cache, event, and MISP refreshes remain outside the transaction.
- Each stage carries its processed story IDs. Core records completion attributes for surviving stories only when the results commit, including successful runs with no findings. Partial enrichment errors do not mark completion. Attributes retain the existing bot-type keys and worker UUID values; instances of the same type share the skip filter.
- Pipeline RQ timeout is `ceil(1.2 × sum(each bot's job timeout))`. Each bot uses `EXECUTION_TIMEOUT` or `RQ_DEFAULT_JOB_TIMEOUT`; `REQUESTS_TIMEOUT` controls only network requests. Pipelines share the combined budget without separate per-stage deadlines. Batch provider wait is separate from each attempt's execution deadline.
- Multi-parent nodes wait only for parents in the current chain. Missing/disabled parents do not block it, but previews warn about them.
- An LLM bot assigned a disabled endpoint is excluded from automatic graphs and cron registration; previews mark its edges disabled. Endpoint and assignment edits refresh registrations without altering the bot's own enabled state. Manual dispatch also rejects disabled endpoints. See [LLM Endpoints](llm-endpoints.md).
- Dependency preview shows the edited bot's connected component. Collector Chain shows the full enabled collector order only for bots in that chain; disabled parents may still appear in dependency badges.
- Bot indexes are unique. Accept integers/integer strings, reject booleans/floats, treat null/empty as omitted, and preserve zero and omitted-update semantics. New forms suggest max+1; availability checks exclude the current bot. Database conflicts retain curated validation errors.
- Use one `POST /api/config/bots/dag-preview`, sending only candidate `id`, `type`, `index`, `enabled`, and the two dependency fields. Reject unrelated fields; malformed previews return a generic 400.
- Preview candidates validate only submitted scheduling parameters, so required execution settings do not block new or existing bot previews. Preview state is never persisted. Omitted run-order fields use their defaults; `RUN_AFTER_COLLECTOR` is a native boolean in list badges and forms.

## Entry Points and Coverage

`src/core/core/model/bot.py`, `src/core/core/managers/queue_manager.py`, `src/core/core/service/task.py`, `src/models/models/admin.py`, `src/worker/worker/bots/bot_tasks.py`, `src/frontend/frontend/views/admin_views/bot_views.py`.

Tests: `src/core/tests/application/admin_console/configuration/test_bot_dag.py`, `src/core/tests/application/worker_pipeline/test_bot_pipeline.py`, `src/core/tests/application/worker_pipeline/test_worker_api.py`, `src/core/tests/unit/test_queue_manager_timeout.py`, `src/core/tests/application/admin_console/configuration/test_queue_manager_scheduler_extended.py`, `src/frontend/tests/unit/views/test_bot_view.py`, `src/frontend/tests/playwright/test_e2e_admin.py`, `src/worker/tests/bots/test_bot_tasks.py`. The timeout workflow inspects real RQ jobs for the combined deadline, inherited filter/user, one-job scheduling, and empty collection runs. Pipeline coverage checks distinct per-bot selections and their union, restrictive limits, exact scope, no-findings completion, retries, collection invalidation, and rollback; bot/collector workflows cover automatic versus manual filters. Worker bot tests register only expected HTTP requests, so unexpected direct writes fail without legacy write mocks.

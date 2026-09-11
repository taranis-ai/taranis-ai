# Bot Run Order DAG

## When To Load

Bot dependencies, `RUN_AFTER_COLLECTOR`, `RUN_AFTER_BOTS`, DAG previews, or post-collection scheduling.

## Contracts

- Bot creation requires an explicitly supplied `name`; `BotCreate` overrides the optional input default. Updates may omit it. Invalid create payloads return a static 400 error, covered by `TestBotConfigApi` in `test_config_api.py`.
- Nodes are configured `Bot.id` UUIDs, never bot types (multiple instances may share a type). `RUN_AFTER_COLLECTOR=true` defines roots; `RUN_AFTER_BOTS` stores comma-separated parent UUIDs edited through the run-order UI.
- Core validates dependencies, self-links, and cycles. Collector runs enqueue the reachable enabled DAG once. Successful manual/cron runs schedule downstream nodes for their `worker_id`; dependent jobs inherit filters and suppress further dependent triggering.
- Multi-parent nodes wait only for parents in the current chain. Missing/disabled parents do not block it, but previews warn about them.
- Dependency preview shows the edited bot's connected component. Collector Chain shows the full enabled collector order only for bots in that chain; disabled parents may still appear in dependency badges.
- Bot indexes are unique. Accept integers/integer strings, reject booleans/floats, treat null/empty as omitted, and preserve zero and omitted-update semantics. New forms suggest max+1; availability checks exclude the current bot. Database conflicts retain curated validation errors.
- Use one `POST /api/config/bots/dag-preview`, sending only candidate `id`, `type`, `index`, `enabled`, and the two dependency fields. Reject unrelated fields; malformed previews return a generic 400.

## Entry Points and Coverage

`src/core/core/model/bot.py`, `src/core/core/managers/queue_manager.py`, `src/core/core/service/task.py`, `src/models/models/admin.py`, `src/worker/worker/bots/bot_tasks.py`, `src/frontend/frontend/views/admin_views/bot_views.py`.

Tests: `src/core/tests/application/admin_console/configuration/test_bot_dag.py`, `src/core/tests/application/admin_console/configuration/test_queue_manager_scheduler_extended.py`, `src/frontend/tests/unit/views/test_bot_view.py`, `src/frontend/tests/playwright/test_e2e_admin.py`, `src/worker/tests/bots/test_bot_tasks.py`.

# Bot Run Order DAG

## When To Load
Bot configuration, post-collection bots, `RUN_AFTER_COLLECTOR`, `RUN_AFTER_BOTS`, bot dependencies, admin bot form, worker bot scheduling.

## Expected Behavior
Each configured bot instance is a DAG node, identified by `Bot.id`. Multiple bot instances may use the same `BOT_TYPES` value. `RUN_AFTER_COLLECTOR=true` marks collector roots. `RUN_AFTER_BOTS` stores comma-separated parent bot instance UUIDs, edited through the admin run-order UI rather than raw text.

The admin dependency preview is scoped to the connected dependency component containing the edited bot. The Collector Chain remains the global enabled collector run order: every bot in that order sees the same full chain, while bots outside it see no Collector Chain section. Disabled bots are excluded from the collector chain but can remain visible in dependency badges with disabled styling. Malformed preview fields, types, or indexes return a generic 400 response rather than exposing validation details or raising a 500.

Collector-triggered runs enqueue the reachable enabled DAG once. Manual and cron bot runs enqueue the downstream DAG for their specific `worker_id` only after a successful result. Dependent jobs inherit the original filter and run with dependent triggering suppressed, so downstream completions do not schedule duplicate chains.

For multiple parents, a bot waits only for parents that are part of the current scheduled chain. Disabled or missing parents do not block a chain, but the preview should warn admins.

## Code Paths
- Core model and DAG validation: `src/core/core/model/bot.py`
- Queue graph scheduling: `src/core/core/managers/queue_manager.py`
- Bot result follow-up scheduling: `src/core/core/service/task.py`
- Worker bot result metadata: `src/worker/worker/bots/bot_tasks.py`
- Admin bot UI: `src/frontend/frontend/views/admin_views/bot_views.py`, `src/frontend/frontend/templates/bot/`
- Seeded defaults: `src/core/core/managers/pre_seed_data.py`

## Data Flow
The normal create/update form posts the full bot configuration. DAG previews use one `POST /api/config/bots/dag-preview` endpoint and send the candidate `id` for stored bots plus `type`, `index`, `enabled`, `RUN_AFTER_COLLECTOR`, and `RUN_AFTER_BOTS`. Core rejects unrelated fields and validates the bot type, dependency UUIDs, self-dependencies, and cycles. Queue scheduling converts bot instance IDs to RQ `depends_on` relationships.

## Testing
- Core DAG tests: `src/core/tests/application/admin_console/configuration/test_bot_dag.py`
- Queue graph tests: `src/core/tests/application/admin_console/configuration/test_queue_manager_scheduler_extended.py`
- Frontend run-order tests: `src/frontend/tests/unit/views/test_bot_view.py`
- Worker metadata tests: `src/worker/worker/tests/bots/test_bot_tasks.py`

## Pitfalls
Do not use bot types as DAG references: they are implementation selectors and are not unique configuration identities. Do not accept type aliases in `RUN_AFTER_BOTS`; this WIP feature has one canonical UUID-based shape. Do not add separate new-bot, stored-bot, or override DAG preview endpoints. Do not send the full bot response model, task status, credentials, or unrelated worker parameters to the preview endpoint. Do not reintroduce type-specific ordering or scheduling special cases. Do not let dependent jobs trigger their own dependents unless the full chain should intentionally recurse.

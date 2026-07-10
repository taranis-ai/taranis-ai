# Bot Run Order DAG

## When To Load
Bot configuration, post-collection bots, `RUN_AFTER_COLLECTOR`, `RUN_AFTER_BOTS`, bot dependencies, admin bot form, worker bot scheduling.

## Expected Behavior
Bot type is the canonical DAG node; Taranis allows one configured bot per `BOT_TYPES` value. `RUN_AFTER_COLLECTOR=true` marks collector roots. `RUN_AFTER_BOTS` stores comma-separated parent bot type names, edited through the admin run-order UI rather than raw text.

The admin DAG preview shows the Collector Chain section only while the edited bot has `RUN_AFTER_COLLECTOR=true`; dependency badges and warnings can still render without that root toggle. Malformed preview types or indexes return a generic 400 response rather than exposing validation details or raising a 500.

Collector-triggered runs enqueue the reachable enabled DAG once. Manual and cron bot runs enqueue their reachable downstream DAG only after a successful result. Dependent jobs inherit the original filter and run with dependent triggering suppressed, so downstream completions do not schedule duplicate chains.

For multiple parents, a bot waits only for parents that are part of the current scheduled chain. Disabled or missing parents do not block a chain, but the preview should warn admins.

## Code Paths
- Core model and DAG validation: `src/core/core/model/bot.py`
- Queue graph scheduling: `src/core/core/managers/queue_manager.py`
- Bot result follow-up scheduling: `src/core/core/service/task.py`
- Worker bot result metadata: `src/worker/worker/bots/bot_tasks.py`
- Admin bot UI: `src/frontend/frontend/views/admin_views/bot_views.py`, `src/frontend/frontend/templates/bot/`
- Seeded defaults: `src/core/core/managers/pre_seed_data.py`

## Data Flow
The admin form posts normal bot parameters. The frontend normalizes the run-order multiselect to `RUN_AFTER_BOTS`, and core validates unknown bot types, self-dependencies, duplicate bot types, and cycles. Queue scheduling converts the DAG to RQ `depends_on` relationships.

## Testing
- Core DAG tests: `src/core/tests/application/admin_console/configuration/test_bot_dag.py`
- Queue graph tests: `src/core/tests/application/admin_console/configuration/test_queue_manager_scheduler_extended.py`
- Frontend run-order tests: `src/frontend/tests/unit/views/test_bot_view.py`
- Worker metadata tests: `src/worker/worker/tests/bots/test_bot_tasks.py`

## Pitfalls
Do not reintroduce type-specific ordering or scheduling special cases. Do not let dependent jobs trigger their own dependents unless the full chain should intentionally recurse. The unique bot-type migration aborts with the duplicate type names instead of deleting configurations; reconcile duplicate bot rows explicitly before retrying the migration.

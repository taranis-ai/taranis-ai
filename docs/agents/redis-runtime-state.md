# Redis Runtime State

## When To Load

Redis configuration, persistence, restart recovery, RQ durability, or cron startup.

## Contracts

- PostgreSQL owns application data, source/bot schedules, completed task results,
  and token revocations. Redis holds disposable caches, coordination leases,
  endpoint health, RQ jobs/registries/dependencies, and materialized cron state.
- Bundled Compose Redis disables both RDB (`save ""`) and AOF (`appendonly no`)
  and mounts `/data` as `tmpfs`. Kubernetes/Helm/ArgoCD retain external Redis;
  operators must apply the same policy at the server and prevent old RDB loading.
- Core startup rebuilds recurring source/bot/housekeeping schedules, endpoint
  probes, and empty word-list downloads. If cron finds no `rq:cron:def`, it calls
  authenticated `POST /worker/cron-jobs` to rebuild through Core. Recovery must
  preserve jobs already accepted into the new Redis instance. Redis/Core outages
  retry on cron's polling interval; existing schedules retain their next-run times
  during normal polling.
- Transient Redis failures must not permanently set the per-process queue error;
  Granian processes reconnect independently without requiring a Core restart.
- Recurring schedules resume at the next occurrence; missed runs are not replayed.
  Pending one-off jobs, retries, delayed MISP pushes, and unfinished bot chains are
  intentionally lost on Redis restart. Without cron, restart Core to rebuild.
  Caches refill on demand; realtime has no history recovery. See
  [Realtime Events](realtime-events.md).

## Entry Points and Coverage

`src/core/core/managers/queue_manager.py`, `src/core/core/api/worker.py`,
`src/worker/worker/cron_scheduler.py`, `src/worker/worker/core_api.py`.

Recovery coverage: `src/core/tests/application/worker_pipeline/test_worker_api.py`
and `src/worker/tests/unit/test_cron_scheduler.py`. The existing scheduled collector
flow in `src/frontend/tests/playwright/test_e2e_rq_tasks.py` flushes the isolated
broker while Core remains running, then verifies recovery and successful execution.
Deployment checks must render
all Compose variants and verify actual Redis persistence settings, empty restarts,
and RAM-backed `/data` on disposable stacks. Operator procedures:
`docker/README.md`, `deploy/README.md`, `dev/README.md`.

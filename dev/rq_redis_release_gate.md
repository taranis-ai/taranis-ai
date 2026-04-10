# RQ/Redis Release Gate

This checklist is for validating the RQ/Redis migration branch before shipping or rebasing again.

## Automated Validation

Run these from the component directory shown.

### Core

```bash
cd src/core
uv sync --all-extras --dev
uv run ruff check
uv run pytest tests/unit tests/functional tests/test_api.py tests/test_schema.py tests/test_settings.py
```

Focus:
- queue startup without `schedule_manager`
- `QueueManager.cancel_job()` removing `rq:cron:def` and `rq:cron:next`
- `/api/health` using Redis/RQ health while preserving `broker` and `workers`
- `/api/config/workers/cron-jobs` and `/api/worker/cron-jobs` using effective collector defaults
- schedule inspection working even if the cron leader is offline

### Frontend

```bash
cd src/frontend
uv sync --all-extras --dev
uv run ruff check
DEBUG=true uv run pytest tests/unit tests/test_settings.py tests/unit/test_router_helpers.py
DEBUG=true uv run pytest tests/playwright/test_e2e_admin.py -k "test_admin_dashboard or test_admin_osint_workflow or test_admin_bot" --e2e-ci
uv run pytest tests/playwright/test_e2e_rq_tasks.py --e2e-ci
```

Focus:
- admin dashboard rendering the merged health payload
- bot and OSINT source CRUD paths against the merged core API
- frontend e2e harness using the RQ-era health semantics

### Worker

```bash
cd src/worker
uv sync --all-extras --dev
uv run ruff check
DEBUG=true uv run pytest worker/tests
```

Focus:
- worker boot against Redis
- cron scheduler behavior
- presenter and publisher regressions introduced by the merge

## Manual Validation

Run manual cutover checks in both environments below.

### Local Dev Validation

Assumption:
- use `./dev/start_dev.sh`

Bootstrap:

```bash
./dev/start_dev.sh
```

Expected local processes after startup:
- support services from `dev/compose.yml`
- `core`
- `frontend`
- `worker`
- `cron`
- optional `rq-dashboard`

Verify:

1. Health and readiness
- `GET /api/health` reports `database`, `seed_data`, `broker`, and `workers` correctly
- `GET /api/isalive` stays green during startup and restart loops
- the admin dashboard renders the merged health payload without errors

2. OSINT source scheduling
- create a scheduled source and confirm an entry appears in `rq:cron:def`
- confirm the same job id has a score in `rq:cron:next`
- edit `REFRESH_INTERVAL` and confirm `rq:cron:next` changes immediately
- disable and re-enable the source and confirm the cron definition is removed and restored
- delete the source and confirm both `rq:cron:def` and `rq:cron:next` entries are gone

3. Bot scheduling
- create a scheduled bot and confirm its `bot_<id>` cron entry exists
- update the schedule and confirm the next-run timestamp refreshes
- disable, re-enable, and delete the bot and confirm Redis cron state follows

4. Immediate task execution
- trigger one collector run
- trigger one bot run
- trigger one presenter run
- trigger one publisher run
- confirm task results and admin views reflect the runs

5. Failure and retry handling
- force one collector or bot failure
- confirm the failure is visible in task results and failed-job views
- retry after fixing the cause and confirm the next run succeeds

6. Scheduler resilience
- stop only the `cron` process
- confirm schedule inspection still shows configured jobs
- confirm execution resumes after restarting `cron`
- restart the worker process independently and confirm no duplicate cron executions occur

### Server Docker Cutover Validation

Assumption:
- the target environment is Docker-based

Target runtime services:
- `ingress`
- `core`
- `frontend`
- `database`
- `redis`
- `collector`
- `workers`
- `cron`

Pre-cutover checks:
- capture the current image tags and environment values
- confirm database backup/restore is available
- confirm Redis is configured for the new stack
- identify and stop any legacy Celery/RabbitMQ services before enabling the RQ stack

Bring-up checks:

```bash
docker compose ps
docker compose logs --tail 200 core workers collector cron redis
```

Verify:

1. Container and API health
- `core`, `collector`, `workers`, `cron`, and `redis` become healthy
- `GET /api/health` reports `database=up`, `seed_data=up`, `broker=up`, and `workers=up`
- ingress and frontend reach the core API successfully

2. Scheduling and Redis state
- create or update one OSINT source and one bot through the running stack
- confirm Redis inside the deployment contains the matching `rq:cron:def` and `rq:cron:next` entries
- confirm deletes remove both entries

3. Task processing
- trigger one collector job and confirm it is processed by `collector`
- trigger one bot, one presenter, and one publisher job and confirm they are processed by `workers`
- confirm task results are visible through the API and admin UI

4. Restart and failover behavior
- restart `cron` only and confirm schedule inspection still works while execution pauses
- restart `workers` only and confirm queues recover normally
- confirm only one active cron leader exists after restart

5. Migration cutover behavior
- verify the stack runs without Celery, APScheduler, or RabbitMQ services
- verify rollback is code/config rollback, not queued-job migration
- verify no operational runbook still points to RabbitMQ or Celery commands

### Shared Redis Checks

Use these during both local and server validation.

Useful commands during manual verification:

```bash
redis-cli HGETALL rq:cron:def
redis-cli ZRANGE rq:cron:next 0 -1 WITHSCORES
redis-cli XLEN rq:cron:events
```

Expected behavior:
- configured cron jobs exist in `rq:cron:def`
- scheduled next-run timestamps exist in `rq:cron:next`
- updates and deletes emit entries in `rq:cron:events`

If Redis only exists inside Docker, use:

```bash
docker compose exec redis redis-cli HGETALL rq:cron:def
docker compose exec redis redis-cli ZRANGE rq:cron:next 0 -1 WITHSCORES
docker compose exec redis redis-cli XLEN rq:cron:events
```

If the target Redis requires authentication, add `-a "$REDIS_PASSWORD"` to those commands.

## Exit Criteria

The branch is ready when:
- automated validation is green
- frontend smoke coverage is green
- manual scheduling and task-execution checks pass
- no Celery, APScheduler, RabbitMQ, or `schedule_manager` runtime assumptions remain

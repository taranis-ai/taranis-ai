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
uv run pytest tests/e2e/test_rq_e2e_tasks.py --e2e-ci
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

Start the stack with one supported workflow:
- `./dev/start_dev.sh`
- manual service startup without tmux
- manual tmux workflow from `dev/README.md`

Then verify:

1. Health and readiness
- `GET /api/health` reports `database`, `seed_data`, `broker`, and `workers` correctly
- `GET /api/isalive` stays green during startup and restart loops

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
- stop the cron scheduler process only
- confirm schedule inspection still shows configured jobs
- confirm execution resumes after restarting the cron scheduler
- restart workers independently and confirm no duplicate cron executions occur

7. Migration cutover checks
- stop Celery/RabbitMQ-era services and confirm the application still operates with Redis/RQ only
- confirm rollback is a code/config rollback, not broker-state migration

## Redis Checks

Useful commands during manual verification:

```bash
redis-cli -a "$REDIS_PASSWORD" HGETALL rq:cron:def
redis-cli -a "$REDIS_PASSWORD" ZRANGE rq:cron:next 0 -1 WITHSCORES
redis-cli -a "$REDIS_PASSWORD" XLEN rq:cron:events
```

Expected behavior:
- configured cron jobs exist in `rq:cron:def`
- scheduled next-run timestamps exist in `rq:cron:next`
- updates and deletes emit entries in `rq:cron:events`

## Exit Criteria

The branch is ready when:
- automated validation is green
- frontend smoke coverage is green
- manual scheduling and task-execution checks pass
- no Celery, APScheduler, RabbitMQ, or `schedule_manager` runtime assumptions remain

---
title: "Background Jobs"
description: Redis, RQ workers, scheduled jobs, and health checks.
weight: 7
---

Taranis AI uses Redis and RQ for background work. Collection, bots, presenters, publishers, connectors, and maintenance jobs are queued by core and processed by worker containers.

## Services

| Service | Purpose |
| --- | --- |
| `redis` | Queue broker, job state, scheduler state, and cache storage. |
| `core` | Creates jobs, stores scheduled job definitions, and exposes `/api/health`. |
| `collector` | Runs collector jobs from the collector queue. |
| `workers` | Runs bots, presenters, publishers, connectors, and miscellaneous jobs. |
| `cron` | Runs `taranis-cron`, reads Redis scheduler definitions, and enqueues due jobs. |

Queues are split by worker category: `collectors`, `bots`, `presenters`, `publishers`, `connectors`, and `misc`.

## Redis settings

Set a Redis password for production and keep Redis private to the Compose or Kubernetes network.

| Variable | Purpose |
| --- | --- |
| `REDIS_URL` | Redis connection URL used by core, frontend, and workers. |
| `REDIS_PASSWORD` | Redis password. |
| `CACHE_REDIS_URL` | Optional dedicated Redis URL for frontend cache. Falls back to `REDIS_URL`. |
| `CACHE_REDIS_PASSWORD` | Optional dedicated cache password. Falls back to `REDIS_PASSWORD`. |
| `RQ_DEFAULT_JOB_TIMEOUT` | Default queued job timeout in seconds. |

Do not publish the Redis port unless you have a controlled operational reason.

## Health checks

Core exposes:

```text
GET /api/health
```

The response reports `database`, `seed_data`, `broker`, and `workers`. If Redis is up but no workers are connected, queued jobs can be accepted but will not run until a worker starts.

Example degraded response:

```json
{
  "healthy": false,
  "services": {
    "database": "up",
    "seed_data": "up",
    "broker": "up",
    "workers": "down"
  }
}
```

When `workers` is `down`, check the `collector`, `workers`, and `cron` containers or deployments first, then inspect worker logs for bad `WORKER_TYPES`, invalid API keys, Redis authentication failures, or failed bot service calls.

## Task failures

The task and Failed Jobs views report terminal RQ failures: unhandled task exceptions, job timeouts, and killed workhorse processes. Failed Jobs includes RQ's exception detail when it is available.

A queued job without a worker, a late schedule, or a blocked queue is an operational liveness problem, not a recorded task failure. Check `/api/health`, the worker containers, and Redis connectivity before treating it as a failed task.

## Scheduled jobs

Collectors and bots use cron-like schedules. Core stores managed schedule definitions in Redis, and the `cron` service reconciles those definitions with enabled sources and bots. Changing a collector or bot schedule does not require restarting the workers.

The worker admin views show queued, active, failed, and scheduled jobs. Use them before clearing queues so you know what work will be lost.

## Upgrade note

Taranis AI 1.4.0 replaced Celery/RabbitMQ with Redis/RQ. There is no queue handover from Celery to RQ. Before upgrading an older deployment, let running Celery jobs finish, stop the old workers, then deploy the Redis, `collector`, `workers`, and `cron` services together.

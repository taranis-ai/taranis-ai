# RQ Migration Guide

Taranis now uses RQ with Redis instead of Celery with RabbitMQ.

Before you migrate, wait for all running and queued Celery tasks to finish. There is no queue handover between RabbitMQ/Celery and Redis/RQ, so in-flight work from the old stack will not continue after cutover.

## Required changes

1. Replace RabbitMQ with Redis in your deployment.
   Why: RQ stores queue and scheduling state in Redis.

2. Check your `compose.yml` or deployment manifests against `docker/compose.yml`.
   Why: the RQ stack expects `redis`, `collector`, `workers`, and `cron`, and no longer uses RabbitMQ, Celery workers, or the old scheduler service.

3. Update `core`, `collector`, `workers`, and `cron` to use `REDIS_URL` and `REDIS_PASSWORD` if needed.
   Why: both API health and background processing now depend on Redis.

4. Pull the new images, restart the stack, and verify `GET /api/health`.
   Why: cutover is complete only when the broker and workers report `up`.

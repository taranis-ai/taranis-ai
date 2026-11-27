---
title: Maintenance
description: Upgrade and maintenance tasks for Taranis AI.
weight: 10
---

## Standard image upgrade

Use published images for deployment upgrades. Do not build application images on production hosts unless you are intentionally testing a custom build.

Only upgrades to the immediately following Taranis AI release are tested and supported. For a larger version gap, upgrade one release at a time and verify the deployment after every step.

```bash
cd taranis-ai/docker
docker compose pull
docker compose up -d
curl -fsS http://<url>:<TARANIS_PORT>/api/health
docker compose ps
```

For rollback, pin `TARANIS_TAG` and `TARANIS_BOT_TAG` to the previous known-good release in `.env`, pull, restart, and verify `/api/health` again.

## Redis/RQ migration

Taranis AI 1.4.0 replaced Celery/RabbitMQ with Redis/RQ. There is no queue handover from old Celery workers to the new RQ workers.

Before upgrading an older deployment:

1. Let running and queued Celery jobs finish.
2. Stop old Celery/RabbitMQ services.
3. Deploy Redis plus the `collector`, `workers`, and `cron` services.
4. Verify `/api/health` reports database, seed data, broker, and workers as `up`.

See [Background Jobs](07_background-jobs.md) for the current worker architecture.

## PostgreSQL 14 to 17

Supported upgrade of PostgreSQL 14.x to PostgreSQL 17.x. Expect Taranis AI downtime during the database upgrade.

### Prerequisites

- Installed [Docker Compose V2](https://docs.docker.com/compose/install/) or [podman-compose](https://github.com/containers/podman-compose)
- Running Taranis AI deployment using the `docker/compose.yml` file.
- Running database PostgreSQL of major version 14
- Compose file (`docker/compose.yml`) is setup to use the image of PostgreSQL 17 (check your `POSTGRES_TAG` variable in the `.env` file)

## Steps to upgrade

1. Go to directory: `taranis-ai/docker`
2. Ensure the script `upgrade-database.sh` is executable
3. Run the script: `./upgrade-database.sh`

All containers should now be up and running again. Verify `/api/health` and review database logs before handing the instance back to users.

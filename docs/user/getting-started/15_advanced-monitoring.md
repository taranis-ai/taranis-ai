---
title: Advanced monitoring
description: Use Sentry for more runtime insights
weight: 15
---

### Prerequisites

- Sentry instance available, either SaaS or self-hosted.
- Follow this [guide](https://docs.sentry.io/product/sentry-basics/integrate-frontend/create-new-project/#create-a-project) to have a Sentry project (and `SENTRY_DSN`) ready.

## What is Sentry

[Sentry](https://sentry.io/welcome/) is a monitoring tool that enables more insights about an application. Taranis AI takes advantage of this if you enable it at the start up.

## What is there to monitor

Sentry can be used to monitor insights about **GUI**, **Core** and **database**. In Taranis AI: *Issues*, *Traces*, *Profiles* and *Queries* can be tracked.

## Health and worker queues

The core service exposes `/api/health` for readiness and dependency checks. It reports the database, seed data, Redis broker, and worker status when those services are available.

Worker-backed actions such as collecting an OSINT source, running a bot, gathering a word list, rendering a product, or publishing a product can be queued even when no workers are connected. In that case the frontend shows a warning that the task was queued but may not be processed until a worker starts.

If this warning appears:

1. Verify Redis with the configured `REDIS_URL` and `REDIS_PASSWORD`.
2. Verify that the `collector`, `cron`, and `workers` containers or Kubernetes deployments are running.
3. Check the worker logs for failed startup, invalid `WORKER_TYPES`, or authentication errors against core.
4. Use the admin worker and queue views to inspect queued, active, failed, and scheduled jobs.

See [Background Jobs](07_background-jobs.md) for worker services, queues, scheduler behavior, and Redis/RQ upgrade notes.

## Audit logging

Core audit logging is enabled by default. It writes structured JSON events to stdout for human-authenticated write requests and login attempts. Events contain request metadata such as the timestamp, path, status, user, and client IP; they never include request bodies, credentials, tokens, or other secrets.

Set `AUDIT_LOG_ENABLED=false` only when log collection is not appropriate for the deployment. Send the core container's stdout to your normal log collector for retention and search.

## How to enable Sentry in Taranis AI

To enable Sentry, set the `SENTRY_DSN` variables in the `.env` file before start of the application. More details about environment variables can be found [here](https://github.com/taranis-ai/taranis-ai/blob/master/docker/README.md).

### GUI monitoring

To gain insights about GUI, use the `TARANIS_GUI_SENTRY_DSN` variable and set it to your Sentry DSN address.

### Core and database monitoring

To gain insights about Core and database, use the `TARANIS_CORE_SENTRY_DSN` variable and set it to your Sentry DSN address.

---
title: "Admin Dashboard"
description: Inspect scheduled work, component versions, system health, and task outcomes.
weight: 30
---

The **Admin Dashboard** is available in [Administration](../admin/_index.md) to users with the corresponding privileges. It includes the Assess, Analyze, Publish, and Connectors statistics described in the [Dashboard overview](_index.md#workflow-cards), followed by operational cards.

## Queue

The **Queue** card shows the number of scheduled tasks and the collection time of the most recent News Item. Select its heading to open the scheduler, where you can inspect:

- **Scheduled Jobs**: work configured or registered to run later.
- **Active Jobs**: work currently in progress.
- **Queue Failures**: jobs held in the RQ failed-job registry.
- **Execution History**: recorded task outcomes and statistics.

The scheduled count includes managed schedules and housekeeping jobs; it is not the number of tasks currently running. **Auto-refresh: 10s** is off by default. When enabled, it refreshes queue cards and the selected Scheduled Jobs, Active Jobs, or Queue Failures tab every ten seconds. Execution History does not poll.

See [Background Jobs](../getting-started/07_background-jobs.md) for queue services and troubleshooting.

## Release Info

**Release Info** lists Core and Frontend separately. Each shows its build date and, when provided by the build, a release tag or commit and branch. Missing build information is shown as **Unavailable**. Use these details when checking which versions are running or reporting a problem.

## System Health

**System Health** reports **Healthy** or **Degraded**, with individual `up`, `down`, or `n/a` badges for:

- **Database**: database availability.
- **Pre-seeded**: initialization data readiness.
- **Redis**: queue broker availability.
- **Workers**: worker availability.

For example, Redis can be up while Workers are down: jobs may be accepted but remain unprocessed until workers are available. Follow the [health-check guidance](../getting-started/07_background-jobs.md#health-checks) to investigate a degraded state.

## Task Status

**Task Status** shows success, warning, and failure counts, plus a total and success-rate bar. Counts use the latest persisted outcome for each worker identity, so repeated runs of the same source or bot do not continually increase the totals.

Warnings contribute to the total but are separate from successes and failures. The success rate counts only full successes. Use Execution History for recorded outcomes and Queue Failures for jobs currently held as failed in the queue system.

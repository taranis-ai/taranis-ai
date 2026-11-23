---
title: "OSINT Sources"
description: "Configure, preview, import, export, and collect OSINT sources."
weight: 3
---

## Functionalities

OSINT Sources define where collectors gather data from. Administrators can:

- Create and edit sources.
- Enable or disable scheduled collection.
- Assign a source rank and icon.
- Preview collector output before ingesting it into Assess.
- Import and export source configuration as JSON.
- Collect one source or all sources on demand.

## Create a new source

1. Select **New Item** to open editor at the bottom.
2. Enter a **Name** and, optionally, a **Description**.
3. Select a collector. See [Collectors](collectors/_index.md).
4. Configure collector parameters.
5. Save the source.

Use **Source Rank** to prioritize or classify sources for analyst workflows. Upload an icon when source identity should be visible on Story and News Item cards.

## Preview a source

Use **Preview** from the source editor or table actions to run the collector without storing the result in Assess. Preview results are shown as Story cards. If a preview fails, use **Retrigger preview** after adjusting the source configuration.

Preview is especially useful for RSS, Simple Web, and RT sources where XPath, headers, proxies, or content extraction settings may need tuning.

## Enable and disable sources

The source state button controls whether the source is active for scheduled collection. Disabling a source unschedules its Redis/RQ cron job; enabling it schedules the source again when it has a refresh interval.

## Import sources

Select **Import** and choose the source JSON file. Imports support current exports and legacy source JSON formats.

## Export sources

Select **Export** to download a JSON file. If sources are selected, only those sources are exported; otherwise all visible sources are exported.

## Collect from sources

Use **Collect** to collect one source, or **Collect All** to collect all enabled sources. Collection is worker-backed; if the job is queued but does not run, verify worker health in [Background Jobs](../getting-started/07_background-jobs.md).

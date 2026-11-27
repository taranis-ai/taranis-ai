---
title: "MISP Auto-Update"
description: "Automatically synchronize Stories to MISP events"
weight: 10
---

MISP Auto-Update pushes Story changes to a selected MISP connector after five minutes without further changes. It is experimental.

## Prerequisites

- A [MISP connector](../admin/connectors.md#misp-connector) is configured.
- You have connector-use permission.

## Enable it

1. Open a Story for editing and select the Advanced layout.
2. Under **MISP auto-update**, select a MISP connector and enable auto-update.
3. Save the Story.

The initial push, and every later eligible change, is scheduled five minutes after the last change. Changing the connector reschedules the push; disabling auto-update cancels it.

## Behavior

- An unsent Story creates a MISP event on its first automatic push.
- Existing events are updated only when owned by your organization. Auto-update skips unowned events.
- External MISP proposals block automatic updates. The Story editor displays a link to the event; resolve the proposals, then change the Story to schedule another push. A successful automatic push clears the warning.
- **Share to Connector** can still push manually, including when auto-update is blocked.
- Enabled Stories show a badge on their cards. Inbound MISP and conflict-resolution changes do not trigger auto-update.

## What is synchronized

- Story title, description, comments, summary, tags, attributes, links, and event report.
- Added and removed news items. Changes to an already-synced news item do not update its MISP object.

Story edits, news-item and tag changes, report membership changes, and Story-modifying bot operations schedule an update.

## Troubleshooting

If no update occurs, confirm auto-update is enabled, the connector works with a manual push, your organization owns the existing event, and no proposal warning is shown. For a proposal warning, resolve the proposals and make another Story change.

## Related functionality

- [MISP Connector](../admin/connectors.md#misp-connector)
- [Assess](_index.md)

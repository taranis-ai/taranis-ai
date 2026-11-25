---
title: "Settings"
description: The settings section enables the administrator to make global changes.
weight: 8
---

### Options

1. Default TLP Level
2. Default Collector Proxy
3. Default Collector Interval
4. [Chat provider settings](chat.md) (when Chat is enabled)

## Default TLP Level

Learn more about what TLP version 2.0 is under [first.org/tlp/](https://www.first.org/tlp/).

**Default value**: Clear

**Options**: Green, Amber, Amber+Strict, Red

All newly collected items by [Collectors](osint-sources.md) use this default TLP value. When this setting is changed, it does not affect the items that are already present in [Assess](../assess/_index.md) section.

This setting can be overridden for each [collector](collectors/_index.md) with the `TLP_LEVEL` field.

## Default Collector Proxy

When a default [collector](collectors/_index.md) proxy is set, it can then be used in the collectors by enabling the switch `USE_GLOBAL_PROXY`.

### The following matrix of the states applies

- 🟢 **Per-source proxy set**: A proxy is set or not for a collector.
- 🔵 **Default proxy set**: A default proxy is set or not in global settings.
- **USE_GLOBAL_PROXY**: In the collector (OSINT Source) settings, the switch `USE_GLOBAL_PROXY` is enabled.
- **Result**: The resulting state.

|  # | Per-source proxy | Default proxy | `USE_GLOBAL_PROXY` | Result                                            |
| -: | :--------------: | :-----------: | :----------------: | :------------------------------------------------ |
|  1 |         ❌        |       ❌       |       `false`      | ⚪ **No proxy**                                    |
|  2 |         ✅        |       ❌       |       `false`      | 🟢 **Per-source proxy**                           |
|  3 |         ❌        |       ✅       |       `false`      | ⚪ **No proxy**                                    |
|  4 |         ✅        |       ✅       |       `false`      | 🟢 **Per-source proxy**                           |
|  5 |         ❌        |       ❌       |       `true`       | ⚪ **No proxy**                                    |
|  6 |         ✅        |       ❌       |       `true`       | ⚪ **No proxy** *(global forced; default missing)* |
|  7 |         ❌        |       ✅       |       `true`       | 🔵 **Default proxy**                              |
|  8 |         ✅        |       ✅       |       `true`       | 🔵 **Default proxy**                              |

## Default Collector Interval

This value is used for `REFRESH_INTERVAL` for all collectors (OSINT Sources) when this field is left unset individually for all collectors. The syntax is the same as `REFRESH_INTERVAL` in [bot settings](bots.md#common-settings).

## Export options

Open **Export Stories** to download an instance-wide JSON array, optionally limited by Story creation date. This requires `ADMIN_OPERATIONS` and does not apply Assess content ACL filtering.

- **All Stories**: Story IDs and creation dates, plus News Item IDs, titles, and content.
- **All Stories With Metadata**: Also includes Story metadata and attributes, and detailed News Items with attributes and tags.

Enter **From** and **To** in your profile timezone, shown beside the form. Both bounds are inclusive. Blank bounds are optional; From alone ends at the current time. Future dates, reversed ranges, and ambiguous or nonexistent local times are rejected.

## Import Stories

Upload an Assess or Admin Story export using **Import Stories**. Both minimal and metadata exports are accepted without manually stripping metadata for compatibility. This is the same importer used by **Assess → Create manual news item → Create from file**, and the import API requires `ASSESS_CREATE`.

Stories are the primary transfer format; existing standalone News Item JSON is also accepted. Imports do not merge or overwrite existing content: duplicate IDs or News Item hashes fail the whole batch. These exports are content transfers, not database backups.

See [Story import and export](../assess/story-transfers.md) for the workflow matrix, accepted formats, source handling, and transfer limits.

## Danger Zone

- **Clear all Worker Queues**: Delete all messages from all worker queues. This action cannot be undone.
- **Delete all Tags**: Delete all tags from all Stories in the system. This action cannot be undone.

See [Background Jobs](../getting-started/07_background-jobs.md) before clearing worker queues.

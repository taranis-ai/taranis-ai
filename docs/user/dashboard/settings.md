---
title: "Tags and Dashboard Settings"
description: Explore tag clusters and customize your Dashboard, including the optional PizzINT signal.
weight: 10
---

## Explore a tag type

Select a **Recently Active Tags** card heading to open its tag table. **Name** identifies the tag and **Size** shows its matching Story count. Sort by either column, use the pagination controls to browse the list, and select a row to open Assess with that tag filter.

The table lists tags across all time for the selected type. The Dashboard's activity window only determines which tags appear on its overview cards; it is not carried into the table or the linked Assess view.

For **Country** and **Location**, the detail view also includes a geographic bubble map. Bubble size represents the matching Story count. The map uses the current table page and interprets names as countries, so arbitrary city or place names may not appear.

## Edit Dashboard

Select **Edit Dashboard** at the top of the Dashboard. These settings belong to your user profile. Choose **Update Dashboard Settings** to save and return to the Dashboard.

| Setting | Default | Effect |
| --- | --- | --- |
| **Activity Window Days** | `7` | Include tags seen in Stories created within this many days. Set `0` to include all activity. Counts still cover all matching Stories. |
| **Show Trending Clusters** | On | Show or hide **Recently Active Tags**. |
| **Select tags** | No selection | Limit cards to selected tag types. Leave empty to include all available types. Despite the label, the choices are types such as Country or Location, rather than individual tag values. |
| **Show Charts in Dashboard** | On | Stores a chart preference. Currently, the Country/Location map renders independently of this switch, so switching it off does not hide that map. |
| **Show PizzINT / DOUGHCON** | Off | Load the PizzINT card under **External Signals**. |

If no recently active tags appear, check that **Show Trending Clusters** is enabled, then widen the activity window or clear the tag-type selection. Cards need tagged Stories matching those settings.

## PizzINT / DOUGHCON

The PizzINT card loads separately after the main Dashboard, so the external request does not delay the workflow cards. It displays:

- **DOUGHCON level** and its readiness description.
- **Smoothed index**, on a scale of 0–100.
- **Observed**, the observation time in your configured timezone.
- **Stale** and **Fetched**, when showing an older result after a refresh problem or an upstream stale response.

The **About DOUGHCON** information button explains the signal, lists all five levels, and attributes the data to PizzINT.watch. The card describes an indicator based on sustained, simultaneous unusual activity at multiple pizza locations.

| Level | Description shown in the card |
| --- | --- |
| 1 | Maximum Readiness |
| 2 | Next Step to Maximum Readiness |
| 3 | Increase in Force Readiness |
| 4 | Increased Intelligence Watch |
| 5 | Lowest State of Readiness |

Results are cached for ten minutes. If refreshing fails, a last successful result can be retained for up to one hour and displayed as **Stale**. When no usable result exists, the card shows **PizzINT data unavailable**. This is a current-status display; it does not collect Stories or maintain a signal history.

As the card's information panel states, this signal is for informational and educational use. Correlation does not imply causation.

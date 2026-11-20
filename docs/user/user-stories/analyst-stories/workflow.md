---
title: Workflow [Analyst]
description: End to End 'user flow' for an analyst.
weight: 15
---

Upon logging in, the analyst is greeted by the Dashboard, which displays significant tags, statistics, and saved Assess filter shortcuts. This view sets the context for the analyst's tasks ahead.

To enhance workflow efficiency, please review the available hotkeys.
Additionally, for simplified filtering, set the "End of Shift" time in the user settings. This feature allows the system to display only articles published since the last end of shift, ensuring you see content that hasn't been reviewed yet.

## Assess
To assess your items, go to the **Assess** section and set the time filter. Apply the **"not read"** and **"not important"** filters. Save this as a default filter if it is your normal review queue. Mark as read any items that have been read but are considered unimportant. Continue working through these items until all are marked as read, focusing only on checking summaries.

Next, set the filter to **"not read"** and **"important"**. Verify the importance of each item and mark it as read if not important. Check whether the item is part of an older report and determine if it still adds value. If not, remove the **"important"** tag and mark the item as read. If multiple items discuss the same topic, merge them.

Use [Omnisearch](../../search/_index.md) for quick jumps, for example `story: tag:ransomware read:false`, `report: weekly`, or `product: stix`.

To update a summary manually or with AI, first click the **"Edit Story"** button. Then, edit the summary yourself or use the AI actions when advanced story edit options are enabled. Send important or sector-specific items via a connector or add them to the relevant reports. Optionally, vote Stories up or down and bookmark Stories that need follow-up.

Finally, remove the **"important"** tag and mark the item as read. For greater efficiency, consider using the time filter to focus on the most recent content.


### Additional tasks during assess
During the review process in the Assess tab, the analyst has several tools at their disposal to optimize their workflow:

**Voting on Stories:**
The analyst can vote stories up or down and mark them as important using buttons or the shortcut (Ctrl+I). This helps highlight stories of particular relevance.

**Mark as Read:**
To maintain efficiency and avoid redundancy, the analyst can mark stories as read or unread using a button or the shortcut (Ctrl+Space).

**Tags:**
Tag filters can be applied to narrow down the selection to the most relevant articles, improving focus. If a story needs editing or creation, the analyst can do so directly within the Assess tab, where news items can be adjusted until they are locked into a report. This ensures the content remains fresh and accurate.

**Bookmarks:**
Bookmark collections are private per user. Use them for follow-up queues, handover topics, and Stories that should stay visible after they are marked read.

**Version history:**
Story version history can be used to inspect how a Story changed over time, especially after manual edits, grouping, ungrouping, bot updates, or connector synchronization.

Once all relevant stories are collected and reviewed, the analyst moves to the Analyze tab to finalize the report and mark it as completed. This step transitions the process from review to dissemination

## Analyze

To analyze your items, go to the Analyze section and review the Report. Add Stories to the appropriate sections, save changes, inspect version history when needed, and mark the Report as completed when it is ready for publication.

## Publish

Finally, the Publish tab is where the compiled Report becomes a Product ready for external consumption. The analyst chooses a Product Type, renders and reviews the final Product preview, then publishes manually or uses autopublish with a default Publisher.

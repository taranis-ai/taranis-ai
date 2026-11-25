---
title: "Story import and export"
description: Share Stories between Taranis AI instances and import existing News Item JSON.
weight: 30
---

Stories are the primary unit for importing and exporting content. Export a Story to transfer its grouped News Items together. Standalone News Items are a secondary import format for existing JSON from an API or another integration; a separate News Item export workflow is not supported or required.

## Choose a workflow

| Goal | Workflow | Result |
| --- | --- | --- |
| Share selected Stories | Assess → select Stories → Share → Export to JSON | Selected Stories with their News Items and metadata. The same action is available on an individual Story. |
| Transfer content across an instance or date range | Admin → Settings → Export Stories | An instance-wide export, optionally restricted by Story creation date, with a choice of minimal content or metadata. |
| Import a Story export as an analyst | Assess → Create manual news item → Create from file | Imports complete Stories, despite the manual News Item page title. |
| Import a Story export from Settings | Admin → Settings → Import Stories | Uses the same importer as Assess. |
| Add an individual article | Assess → Create manual news item | Enter content manually or use Create from URL. Use Create from file when you already have News Item JSON. |

## Export selected Stories in Assess

Open **Share** on a Story, or select multiple Stories and use the bulk sharing action. Choose **Export to JSON**.

The download includes Story and News Item attributes and News Item tags. Its JSON envelope is `{ "total_count": ..., "items": [...] }`.

Export requires Assess access (`ASSESS_ACCESS`), read access to every linked source, and access to the TLP levels of both the Stories and their News Items. Read-only source access is sufficient. If any selected Story is missing or inaccessible, the whole export fails without downloading a partial file. Reload Assess and retry with an accessible selection.

## Export Stories in Admin Settings

Open **Settings → Export Stories** and choose:

- **All Stories**: Story IDs and creation dates, plus News Item IDs, titles, and content. Other metadata is omitted; imported Story titles are derived from their News Items.
- **All Stories With Metadata**: Story content and metadata, including Story attributes and detailed News Items with attributes and tags.

Both downloads are JSON arrays. Both can be imported through either import screen without manually removing metadata to make the format compatible.

Admin export requires `ADMIN_OPERATIONS` and covers the instance without the content ACL filtering used by Assess exports. Use Assess export when you only want to share selected accessible Stories.

**From** and **To** filter the Story's creation time, with inclusive bounds. Enter dates in your profile timezone, shown beside the form; Taranis converts each boundary to UTC using the applicable daylight-saving offset. Blank bounds are optional. From alone ends at the current time. Future dates, reversed ranges, and local times skipped or repeated during a daylight-saving transition are rejected.

## Import through Assess or Settings

Upload the JSON file using **Create from file** in Assess or **Import Stories** in Settings. Both entry points use the same import behavior and require `ASSESS_CREATE` at the API. Access to the Settings screen does not define a separate import format.

| Input file | Assess Create from file | Settings Import Stories |
| --- | --- | --- |
| Assess Story export | Supported | Supported |
| Admin minimal Story export | Supported | Supported |
| Admin Story export with metadata | Supported | Supported |
| Single Story object or array of Stories | Supported | Supported |
| Single News Item object or array of News Items | Supported | Supported |

Do not mix Story objects and standalone News Item objects in the same array. Successful imports from **Create from file** return you to Assess.

### Standalone News Items

Use this secondary format when an integration supplies individual News Items instead of grouped Stories. For example:

```json
{
  "title": "Example article",
  "content": "Article text supplied by an integration.",
  "source": "Example publication",
  "link": "https://example.com/article"
}
```

Each imported standalone News Item receives a new parent Story so it appears in Assess. An exported `story_id` is ignored in this case; importing individual items does not recreate their former grouping or add them to an existing Story. Import a complete Story when you need to preserve its grouping.

## Transfer limits

- **No merging or overwriting:** exported IDs are retained. An existing ID or duplicate News Item hash causes the entire import to fail. Invalid batches also roll back completely. Re-importing an export into an instance that still contains that content is not an update workflow.
- **Sources are not created by a Story import:** a source reference that exists in the destination can be retained; a missing reference falls back to the manual source. Minimal exports omit source references and therefore use the manual source.
- **Metadata depends on the export:** minimal Admin exports omit tags, attributes, links, and other metadata. Assess and Admin metadata exports retain supported metadata, but are not full copies of the originating instance.
- **These are content transfers, not backups:** bookmarks, individual user votes, report relationships, and local ordering settings are not restored. Import creates a new revision record rather than restoring the original revision history.

Review the imported content and its destination source before continuing your normal Assess workflow.

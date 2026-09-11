# Exporting stories

In **Settings → Export Stories**, administrators can download an instance-wide JSON array. **All Stories** contains story IDs, creation dates, and news-item IDs, titles, and content. **All Stories With Metadata** also contains story attributes, news-item attributes/tags, and the existing story metadata.

From and To are inclusive bounds on the story's creation date, entered in **UTC**. Empty fields leave that bound open; From alone ends at the current time. Future dates and a To earlier than From are rejected. API clients may send explicit timezone offsets, which Core normalizes to UTC.

In **Assess → story actions → Share → Export to JSON**, the download contains the selected stories as `{ "total_count": ..., "items": [...] }`. The same action supports bulk selections. Exports read fresh data and include story and news-item attributes. If any selected story is missing or inaccessible, no partial file is downloaded: reload Assess and retry with an accessible selection. Read-only access is sufficient, but every linked source and both story/news-item TLP levels must be accessible.

Both formats can be imported through the existing story import form. They are content transfers, not database backups: local ordering, bookmarks, user votes, and report relationships are not restored. Exported news-item arrays reflect the current local display order; import does not change the destination's local ordering policy. Selected exports retain the shared import-field allowlists and omit UI-only fields.

## Implementation and measurement

`Story.to_export_dict()` adds story attributes without calling the detail serializer or querying report counts. Settings metadata and selected exports use batched relationship loading. Worker tags and attributes remain maps for NLP/MISP consumers.

A local SQLite comparison used 50 stories, four news items per story, ten tags per news item, and five runs with the ORM identity map cleared between runs. The old metadata query plus `to_dict()` took a median 50.48 ms and 502 SQL queries; the batched export including story attributes took 16.05 ms and 7 queries. These are local measurements, not production throughput guarantees. To reproduce, seed that dataset in an isolated test database and compare `select(Story).join(NewsItem)` plus `to_dict()` against `StoryService.export_with_metadata(None, None)`, counting `before_cursor_execute` events.

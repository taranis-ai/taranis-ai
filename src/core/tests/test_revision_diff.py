from models.revision_diff import build_report_revision_diff_payload, build_story_revision_diff_payload


def test_build_story_revision_diff_payload_formats_inline_and_collection_changes():
    payload = build_story_revision_diff_payload(
        "story-1",
        "Story title",
        {
            "id": 1,
            "revision": 1,
            "created_at": "2026-03-12T10:00:00",
            "created_by": "alice",
            "created_by_id": 1,
            "note": "created",
            "data": {
                "title": "Kill Chain im Krieg verkurzt",
                "description": "First draft",
                "summary": "Summary A",
                "comments": "Comment A",
                "likes": 1,
                "dislikes": 0,
                "tags": [{"name": "old-tag"}],
                "news_items": [{"id": "news-1", "title": "Old news"}],
                "attributes": [{"key": "TLP", "value": "clear"}],
            },
        },
        {
            "id": 2,
            "revision": 2,
            "created_at": "2026-03-12T11:00:00",
            "created_by": "bob",
            "created_by_id": 2,
            "note": "update",
            "data": {
                "title": "Kill Chain im Krieg deutlich verkurzt",
                "description": "First draft",
                "summary": "Summary B",
                "comments": "Comment A",
                "likes": 3,
                "dislikes": 1,
                "tags": [{"name": "new-tag"}],
                "news_items": [{"id": "news-2", "title": "New news"}],
                "attributes": [{"key": "TLP", "value": "amber"}],
            },
        },
    )

    assert payload.resource.model_dump(mode="json") == {"id": "story-1", "title": "Story title"}
    assert payload.from_revision.revision == 1
    assert payload.to_revision.created_by == "bob"

    title_change = next(change for change in payload.changes if change.field == "Title")
    assert any(segment.highlighted for segment in title_change.new_segments)
    assert title_change.old_segments
    assert any(change.field == "Tags Added" and change.new_value == "new-tag" for change in payload.changes)
    assert any(change.field == "News Items Added" and change.new_value == "New news" for change in payload.changes)
    assert any(change.field == "Likes" and change.old_value == 1 and change.new_value == 3 for change in payload.changes)
    assert any(change.field == "Dislikes" and change.old_value == 0 and change.new_value == 1 for change in payload.changes)
    assert any(change.field == "TLP" and change.old_value == "clear" and change.new_value == "amber" for change in payload.changes)


def test_build_story_revision_diff_payload_returns_no_changes_for_identical_data():
    payload = build_story_revision_diff_payload(
        "story-1",
        "Story title",
        {
            "id": 1,
            "revision": 1,
            "created_at": "2026-03-12T10:00:00",
            "created_by": "alice",
            "created_by_id": 1,
            "note": "created",
            "data": {"title": "Story title", "tags": [], "news_items": [], "attributes": []},
        },
        {
            "id": 2,
            "revision": 2,
            "created_at": "2026-03-12T11:00:00",
            "created_by": "bob",
            "created_by_id": 2,
            "note": "update",
            "data": {"title": "Story title", "tags": [], "news_items": [], "attributes": []},
        },
    )

    assert payload.changes == []


def test_build_report_revision_diff_payload_formats_story_and_group_changes():
    payload = build_report_revision_diff_payload(
        "report-1",
        "Report title",
        {
            "id": 1,
            "revision": 1,
            "created_at": "2026-03-12T10:00:00",
            "created_by": "alice",
            "created_by_id": 1,
            "note": "created",
            "data": {
                "title": "Report Draft",
                "completed": False,
                "stories": [{"id": "story-1", "title": "Story One"}],
                "grouped_attributes": [
                    {
                        "title": "Summary",
                        "attributes": [{"title": "Threat", "type": "STORY", "value": "story-1"}],
                    }
                ],
            },
        },
        {
            "id": 2,
            "revision": 2,
            "created_at": "2026-03-12T11:00:00",
            "created_by": "bob",
            "created_by_id": 2,
            "note": "update",
            "data": {
                "title": "Report Final",
                "completed": True,
                "stories": [{"id": "story-2", "title": "Story Two"}],
                "grouped_attributes": [
                    {
                        "title": "Summary",
                        "attributes": [{"title": "Threat", "type": "STORY", "value": "story-2"}],
                    }
                ],
            },
        },
    )

    assert payload.resource.model_dump(mode="json") == {"id": "report-1", "title": "Report title"}
    assert any(change.field == "Title" for change in payload.changes)
    assert any(change.field == "Completed" and change.new_value is True for change in payload.changes)
    assert any(
        change.field == "Threat" and change.group == "Summary" and change.old_value == "Story One" and change.new_value == "Story Two"
        for change in payload.changes
    )
    assert any(change.field == "Stories Added" and change.new_value == "Story Two" for change in payload.changes)
    assert any(change.field == "Stories Removed" and change.old_value == "Story One" for change in payload.changes)


def test_build_report_revision_diff_payload_returns_no_changes_for_identical_data():
    payload = build_report_revision_diff_payload(
        "report-1",
        "Report title",
        {
            "id": 1,
            "revision": 1,
            "created_at": "2026-03-12T10:00:00",
            "created_by": "alice",
            "created_by_id": 1,
            "note": "created",
            "data": {"title": "Report title", "completed": False, "stories": [], "grouped_attributes": []},
        },
        {
            "id": 2,
            "revision": 2,
            "created_at": "2026-03-12T11:00:00",
            "created_by": "bob",
            "created_by_id": 2,
            "note": "update",
            "data": {"title": "Report title", "completed": False, "stories": [], "grouped_attributes": []},
        },
    )

    assert payload.changes == []

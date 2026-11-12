import uuid

import pytest

from core.managers.db_manager import db
from core.model.news_item_conflict import NewsItemConflict
from core.model.story import Story
from tests.application.support.builders import build_news_item_payload, create_story


@pytest.fixture
def conflict_store():
    NewsItemConflict.flush_store()
    yield
    NewsItemConflict.flush_store()


@pytest.mark.usefixtures("session")
def test_add_selected_items_clears_resolved_conflict_and_reevaluates_the_rest(
    client,
    auth_header,
    conflict_store,
    monkeypatch,
):
    remaining_story_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    resolved_story_id = str(uuid.uuid4())
    NewsItemConflict.register(resolved_story_id, "resolved-item", "existing-story", {"id": resolved_story_id})
    for story_id in remaining_story_ids:
        NewsItemConflict.register(story_id, f"{story_id}-item", "existing-story", {"id": story_id})
    reevaluated = []

    def rebuild(snapshot):
        story_id = snapshot["id"]
        reevaluated.append(story_id)
        NewsItemConflict.register(story_id, f"{story_id}-item", "existing-story", snapshot)
        return {"error": {"conflicts_number": 1}}, 409

    monkeypatch.setattr(Story, "add_or_update", rebuild)
    news_item = build_news_item_payload()

    response = client.post(
        "/api/connectors/conflicts/news-items",
        json={"incoming_story_id": resolved_story_id, "news_items": [news_item]},
        headers=auth_header,
    )

    assert response.status_code == 200
    assert response.get_json() == {"message": "News items added successfully", "added_ids": [news_item["id"]]}
    assert resolved_story_id not in NewsItemConflict.story_index
    assert all(conflict.incoming_story_id != resolved_story_id for conflict in NewsItemConflict.conflict_store.values())
    assert reevaluated == remaining_story_ids
    assert set(NewsItemConflict.story_index) == set(remaining_story_ids)
    assert {conflict.incoming_story_id for conflict in NewsItemConflict.conflict_store.values()} == set(remaining_story_ids)


@pytest.mark.usefixtures("session")
def test_inbound_resolution_only_cancels_deleted_candidates(
    client,
    auth_header,
    admin_user,
    conflict_store,
    monkeypatch,
):
    surviving_story = create_story(news_items=[build_news_item_payload()])
    deleted_story = create_story(news_items=[build_news_item_payload()])
    NewsItemConflict.register(surviving_story.id, "conflicting-item", deleted_story.id, {"id": surviving_story.id})
    cancelled = []
    refreshed = []
    ungrouped_by = []

    monkeypatch.setattr(Story, "delete_news_items", lambda news_item_ids: None)

    def ungroup(story_ids, user):
        ungrouped_by.append(user.id)
        db.session.delete(deleted_story)
        db.session.commit()
        return {"message": "Ungrouping Stories successful"}, 200

    monkeypatch.setattr(Story, "ungroup_multiple_stories", ungroup)
    monkeypatch.setattr(
        Story,
        "add",
        lambda incoming_story: ({"message": "Story added successfully", "story_id": incoming_story["id"]}, 200),
    )
    monkeypatch.setattr("core.service.news_item_conflict.cancel_misp_auto_update_jobs", cancelled.extend)
    monkeypatch.setattr("core.service.story.refresh_misp_auto_update_jobs", refreshed.extend)

    response = client.put(
        "/api/connectors/conflicts/news-items",
        json={
            "existing_story_ids": [surviving_story.id, deleted_story.id],
            "incoming_news_item_ids": ["conflicting-item"],
            "incoming_story": {"id": surviving_story.id},
            "remaining_stories": [],
        },
        headers=auth_header,
    )

    assert response.status_code == 200
    assert response.get_json() == {"message": "Story added successfully", "story_id": surviving_story.id}
    assert cancelled == [deleted_story.id]
    assert refreshed == []
    assert ungrouped_by == [admin_user.id]
    assert surviving_story.id not in NewsItemConflict.story_index
    assert not NewsItemConflict.conflict_store

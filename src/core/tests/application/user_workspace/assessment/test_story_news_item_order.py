import pytest

from core.managers.db_manager import db
from core.model.story import Story
from tests.application.support.builders import build_news_item_payload, create_story


pytestmark = pytest.mark.usefixtures("session")


def test_order_saves_without_changing_content_and_rejects_stale_or_invalid_requests(client, auth_header):
    story = create_story(news_items=[build_news_item_payload() for _ in range(3)])
    original_ids = [item.id for item in story.ordered_news_items]
    desired_ids = list(reversed(original_ids))
    before = (story.title, story.updated, story.revision, story.last_change)
    endpoint = f"/api/assess/stories/{story.id}/news-item-order"
    payload = {"news_item_ids": desired_ids, "expected_news_item_ids": original_ids}

    response = client.put(endpoint, headers=auth_header, json=payload)
    assert response.status_code == 200
    db.session.expire_all()
    assert [item.id for item in story.ordered_news_items] == desired_ids
    assert (story.title, story.updated, story.revision, story.last_change) == before
    detail = client.get(f"/api/assess/stories/{story.id}", headers=auth_header).get_json()
    assert [item["id"] for item in detail["news_items"]] == desired_ids
    assert detail["can_order_news_items"] is True
    assert "news_item_order" not in story.to_worker_dict()

    assert client.put(endpoint, headers=auth_header, json=payload).status_code == 409
    for invalid in (desired_ids[:-1], [desired_ids[0]] * 3, [*desired_ids[:-1], "foreign-item"]):
        response = client.put(endpoint, headers=auth_header, json={"news_item_ids": invalid, "expected_news_item_ids": desired_ids})
        assert response.status_code == 400
    assert [item.id for item in story.ordered_news_items] == desired_ids


def test_grouping_and_ungrouping_preserve_editorial_order_and_title_fallback(admin_user):
    target = create_story(news_items=[build_news_item_payload() for _ in range(3)])
    source = create_story(news_items=[build_news_item_payload() for _ in range(2)])
    target.news_item_order = [item.id for item in reversed(target.ordered_news_items)]
    source.news_item_order = [item.id for item in reversed(source.ordered_news_items)]
    expected = target.news_item_order + source.news_item_order
    target.title = target.ordered_news_items[0].title
    fallback_title = target.ordered_news_items[1].title
    db.session.commit()

    result, status = Story.group_stories([target.id, source.id], user=admin_user)
    assert status == 200, result
    db.session.expire_all()
    assert [item.id for item in target.ordered_news_items] == expected

    result, status = Story.ungroup_news_items_from_story([expected[0]], user=admin_user)
    assert status == 200, result
    db.session.expire_all()
    assert [item.id for item in target.ordered_news_items] == expected[1:]
    assert target.title == fallback_title
    detached = Story.get(result["new_stories_ids"][0])
    assert detached.title == detached.news_items[0].title

    target.title = "Analyst-written title"
    db.session.commit()
    result, status = Story.ungroup_news_items_from_story([expected[1]], user=admin_user)
    assert status == 200, result
    assert target.title == "Analyst-written title"


def test_external_updates_and_conflict_resolution_preserve_local_order(admin_user):
    story = create_story(news_items=[build_news_item_payload() for _ in range(3)])
    story.news_item_order = [item.id for item in reversed(story.ordered_news_items)]
    expected = list(story.news_item_order)
    db.session.commit()
    payload = story.to_worker_dict()
    payload["news_items"].reverse()
    payload["news_item_order"] = list(reversed(expected))
    payload["summary"] = "Updated upstream"
    result, status = Story.add_or_update(payload)
    assert status == 200, result
    db.session.expire_all()
    assert [item.id for item in story.ordered_news_items] == expected
    assert story.summary == "Updated upstream"

    from core.model.story_conflict import StoryConflict

    upstream = story.to_worker_dict()
    upstream["summary"] = "Resolved upstream"
    try:
        Story.update_with_conflicts(story.id, upstream)
        result, status = StoryConflict.conflict_store[story.id].resolve({}, admin_user)
        assert status == 200, result
        db.session.expire_all()
        assert [item.id for item in story.ordered_news_items] == expected
        assert story.summary == "Resolved upstream"
    finally:
        StoryConflict.conflict_store.pop(story.id, None)

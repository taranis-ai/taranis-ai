import pytest

from core.managers.db_manager import db
from core.model.connector import Connector
from core.model.story import Story
from core.service.misp_story_sync import apply_misp_auto_update_blocked, apply_misp_sync_story_result
from tests.application.support.builders import build_news_item_payload, create_story


def _misp_connector(name: str) -> Connector:
    connector = Connector(name=name, description="", type="misp_connector")
    db.session.add(connector)
    db.session.commit()
    return connector


def _story():
    return create_story(news_items=[build_news_item_payload()])


@pytest.mark.usefixtures("session")
def test_misp_auto_update_only_stores_configuration(monkeypatch):
    monkeypatch.setattr("core.service.misp_auto_update.schedule_story_update", lambda story: None)
    story = _story()
    first_connector = _misp_connector("First MISP")
    second_connector = _misp_connector("Second MISP")

    assert Story.update(story.id, {"misp_auto_update": {"connector_id": first_connector.id, "enabled": True}})[1] == 200
    sync = story.misp_auto_update
    assert sync is not None
    assert sync.to_public_dict() == {"connector_id": first_connector.id, "enabled": True}

    assert Story.update(story.id, {"misp_auto_update": {"connector_id": second_connector.id, "enabled": True}})[1] == 200
    assert Story.update(story.id, {"misp_auto_update": {"connector_id": second_connector.id, "enabled": False}})[1] == 200
    assert sync.to_public_dict() == {"connector_id": second_connector.id, "enabled": False}


@pytest.mark.usefixtures("session")
def test_auto_update_proposals_are_stored_on_the_story(monkeypatch):
    monkeypatch.setattr("core.service.misp_auto_update.schedule_story_update", lambda story: None)
    story = _story()
    connector = _misp_connector("MISP")
    Story.update(story.id, {"misp_auto_update": {"connector_id": connector.id, "enabled": True}})
    sync = story.misp_auto_update
    assert sync is not None

    proposal_url = "https://misp.example/events/view/event-1"
    assert apply_misp_auto_update_blocked({"story_id": story.id, "proposal_url": proposal_url})
    assert sync.enabled is True
    assert story.find_attribute_by_key("has_proposals").value == proposal_url

    payload = {
        "type": "misp_sync_story",
        "story_id": story.id,
        "misp_event_uuid": "320d4589-cd71-4722-aa28-ea5530e99830",
        "news_item_ids_to_mark_external": [],
    }
    assert apply_misp_sync_story_result(payload)
    assert story.find_attribute_by_key("has_proposals").value == proposal_url

    assert apply_misp_sync_story_result(payload, clear_auto_update_proposals=True)
    assert story.find_attribute_by_key("has_proposals") is None

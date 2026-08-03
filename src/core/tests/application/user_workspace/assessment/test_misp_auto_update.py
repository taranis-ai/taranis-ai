from types import SimpleNamespace

import pytest

from core.managers.db_manager import db
from core.model.connector import Connector
from core.model.story import Story
from core.service.misp_story_sync import apply_misp_auto_update_blocked, apply_misp_sync_story_result, handle_misp_connector_result
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
def test_misp_auto_update_requires_connector_access(client, auth_header, auth_header_user_permissions, monkeypatch):
    monkeypatch.setattr("core.service.misp_auto_update.schedule_story_update", lambda story: None)
    story = _story()
    connector = _misp_connector("MISP")

    payload = {"misp_auto_update": {"connector_id": connector.id, "enabled": True}}
    assert client.patch(f"/api/assess/stories/{story.id}", json=payload, headers=auth_header_user_permissions).status_code == 403
    assert client.patch(f"/api/assess/stories/{story.id}", json={"title": "Updated"}, headers=auth_header_user_permissions).status_code == 200
    assert client.patch(f"/api/assess/stories/{story.id}", json=payload, headers=auth_header).status_code == 200

    monkeypatch.setattr(
        Connector, "get", lambda connector_id: SimpleNamespace(id=connector_id, type=SimpleNamespace(value="other_connector"))
    )
    invalid_payload = {"misp_auto_update": {"connector_id": "not-a-misp-connector", "enabled": True}}
    assert client.patch(f"/api/assess/stories/{story.id}", json=invalid_payload, headers=auth_header).status_code == 400
    assert Story.get(story.id).title == story.title
    assert Story.get(story.id).attributes == story.attributes


@pytest.mark.usefixtures("session")
def test_invalid_auto_update_does_not_apply_other_story_changes(client, auth_header, monkeypatch):
    monkeypatch.setattr("core.service.misp_auto_update.schedule_story_update", lambda story: None)
    story = _story()
    original_title = story.title

    response = client.patch(
        f"/api/assess/stories/{story.id}",
        json={
            "title": "Should not persist",
            "attributes": [{"key": "new_attribute", "value": "Should not persist"}],
            "misp_auto_update": {"connector_id": "not-a-misp-connector", "enabled": True},
        },
        headers=auth_header,
    )

    assert response.status_code == 400
    db.session.expire_all()
    unchanged_story = Story.get(story.id)
    assert unchanged_story.title == original_title
    assert unchanged_story.find_attribute_by_key("new_attribute") is None


@pytest.mark.usefixtures("session")
def test_auto_update_proposals_are_stored_on_the_story(monkeypatch):
    monkeypatch.setattr("core.service.misp_auto_update.schedule_story_update", lambda story: None)
    story = _story()
    connector = _misp_connector("MISP")
    Story.update(story.id, {"misp_auto_update": {"connector_id": connector.id, "enabled": True}})
    sync = story.misp_auto_update
    assert sync is not None

    proposal_url = "https://misp.example/events/view/event-1"
    previous_updated = story.updated
    previous_revision = story.revision
    assert apply_misp_auto_update_blocked({"story_id": story.id, "proposal_url": proposal_url})
    db.session.refresh(story)
    assert sync.enabled is True
    assert story.find_attribute_by_key("has_proposals").value == proposal_url
    assert story.updated > previous_updated
    assert story.revision == previous_revision + 1

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


@pytest.mark.usefixtures("session")
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"story_id": 1, "proposal_url": "https://misp.example/events/view/event-1"},
        {"story_id": "story-1"},
        {"story_id": "story-1", "proposal_url": 1},
    ],
)
def test_invalid_auto_update_blocked_payload_does_not_change_story(payload):
    story = _story()
    previous_attributes = [attribute.to_small_dict() for attribute in story.attributes]
    previous_revision = story.revision

    assert not apply_misp_auto_update_blocked(payload)
    db.session.refresh(story)
    assert [attribute.to_small_dict() for attribute in story.attributes] == previous_attributes
    assert story.revision == previous_revision


@pytest.mark.usefixtures("session")
def test_auto_update_blocked_payload_for_missing_story_does_not_change_database():
    story = _story()
    previous_attributes = [attribute.to_small_dict() for attribute in story.attributes]
    previous_revision = story.revision

    assert not apply_misp_auto_update_blocked({"story_id": "missing-story", "proposal_url": "https://misp.example/events/view/event-1"})
    db.session.refresh(story)
    assert [attribute.to_small_dict() for attribute in story.attributes] == previous_attributes
    assert story.revision == previous_revision


@pytest.mark.usefixtures("session")
def test_malformed_sync_results_do_not_skip_valid_results():
    story = _story()

    handle_misp_connector_result(
        {
            "connector_type": "MISP_CONNECTOR",
            "connector_id": "connector-1",
            "sync_results": [
                None,
                {"type": "misp_sync_story", "story_id": story.id, "misp_event_uuid": "event-1", "news_item_ids_to_mark_external": []},
            ],
        }
    )

    assert story.find_attribute_by_key("misp_event_uuid").value == "event-1"

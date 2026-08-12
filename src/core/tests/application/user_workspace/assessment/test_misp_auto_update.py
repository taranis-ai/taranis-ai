from types import SimpleNamespace

import pytest

from core.managers.db_manager import db
from core.model.connector import Connector
from core.model.report_item import ReportItem
from core.model.report_item_type import ReportItemType
from core.model.story import Story
from core.service.misp_story_sync import apply_misp_auto_update_blocked, apply_misp_sync_story_result, handle_misp_connector_result
from core.service.news_item_tag import NewsItemTagService
from core.service.story import StoryService
from tests.application.support.builders import build_news_item_payload, create_osint_source, create_story


def _misp_connector(name: str) -> Connector:
    connector = Connector(name=name, description="", type="misp_connector")
    db.session.add(connector)
    db.session.commit()
    return connector


def _story():
    return create_story(news_items=[build_news_item_payload()])


@pytest.mark.usefixtures("session")
def test_misp_auto_update_only_stores_configuration(admin_user, monkeypatch):
    monkeypatch.setattr("core.service.misp_auto_update.refresh_misp_auto_update_job", lambda story_id: None)
    story = _story()
    first_connector = _misp_connector("First MISP")
    second_connector = _misp_connector("Second MISP")

    assert Story.update(story.id, {"misp_auto_update": {"connector_id": first_connector.id, "enabled": True}}, admin_user)[1] == 200
    sync = story.misp_auto_update
    assert sync is not None
    assert sync.to_dict() == {"connector_id": first_connector.id, "enabled": True}

    assert Story.update(story.id, {"misp_auto_update": {"connector_id": second_connector.id, "enabled": True}}, admin_user)[1] == 200
    assert Story.update(story.id, {"misp_auto_update": {"connector_id": second_connector.id, "enabled": False}}, admin_user)[1] == 200
    assert sync.to_dict() == {"connector_id": second_connector.id, "enabled": False}


@pytest.mark.usefixtures("session")
def test_misp_auto_update_requires_connector_access(client, auth_header, auth_header_user_permissions, monkeypatch):
    monkeypatch.setattr("core.service.misp_auto_update.refresh_misp_auto_update_job", lambda story_id: None)
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
def test_bot_story_update_ignores_misp_auto_update(client, api_header, admin_user, monkeypatch):
    refreshed = []
    monkeypatch.setattr("core.service.misp_auto_update.refresh_misp_auto_update_job", refreshed.append)
    story = _story()
    first_connector = _misp_connector("First MISP")
    second_connector = _misp_connector("Second MISP")
    assert (
        Story.update(
            story.id,
            {"misp_auto_update": {"connector_id": first_connector.id, "enabled": True}},
            admin_user,
        )[1]
        == 200
    )

    response = client.put(
        f"/api/bots/story/{story.id}",
        json={"title": "Bot title", "misp_auto_update": {"connector_id": second_connector.id, "enabled": False}},
        headers=api_header,
    )

    assert response.status_code == 200
    assert story.title == "Bot title"
    assert story.misp_auto_update.to_dict() == {"connector_id": first_connector.id, "enabled": True}
    assert refreshed == [story.id]


@pytest.mark.usefixtures("session")
def test_misp_auto_update_configuration_requires_an_explicit_user():
    story = _story()
    connector = _misp_connector("MISP")

    response, status = Story.update(story.id, {"misp_auto_update": {"connector_id": connector.id, "enabled": True}})

    assert status == 403
    assert response == {"error": "forbidden"}
    assert story.misp_auto_update is None


@pytest.mark.usefixtures("session")
def test_blank_disabled_misp_auto_update_is_normalized_at_api_boundary(client, auth_header, monkeypatch):
    monkeypatch.setattr("core.service.misp_auto_update.refresh_misp_auto_update_job", lambda story_id: None)
    story = _story()

    response = client.patch(
        f"/api/assess/stories/{story.id}",
        json={"title": "Updated", "misp_auto_update": {"connector_id": "", "enabled": False}},
        headers=auth_header,
    )

    assert response.status_code == 200
    assert Story.get(story.id).title == "Updated"
    assert Story.get(story.id).misp_auto_update is None


@pytest.mark.usefixtures("session")
def test_story_list_serializes_misp_auto_update(admin_user):
    story = _story()
    connector = _misp_connector("MISP")
    assert Story.update(story.id, {"misp_auto_update": {"connector_id": connector.id, "enabled": True}}, admin_user)[1] == 200

    assert story.to_dict()["misp_auto_update"] == {"connector_id": connector.id, "enabled": True}


@pytest.mark.usefixtures("session")
def test_refreshing_deleted_story_cancels_queued_update(admin_user, monkeypatch):
    story = _story()
    cancelled = []
    monkeypatch.setattr("core.service.misp_auto_update.queue_manager.queue_manager.cancel_job", cancelled.append)

    assert StoryService.delete(story.id, admin_user)[1] == 200

    assert Story.get(story.id) is None
    assert cancelled == [f"misp_auto_update_{story.id.replace('-', '_')}"]


@pytest.mark.usefixtures("session")
def test_grouping_cancels_absorbed_story_update(admin_user, monkeypatch):
    target = _story()
    absorbed = _story()
    connector = _misp_connector("MISP")
    assert Story.update(absorbed.id, {"misp_auto_update": {"connector_id": connector.id, "enabled": True}}, admin_user)[1] == 200
    cancelled = []
    monkeypatch.setattr("core.service.misp_auto_update.queue_manager.queue_manager.cancel_job", cancelled.append)

    assert StoryService.group_stories([target.id, absorbed.id], admin_user)[1] == 200

    assert Story.get(absorbed.id) is None
    assert cancelled == [f"misp_auto_update_{absorbed.id.replace('-', '_')}"]


@pytest.mark.usefixtures("session")
def test_bot_ungroup_noop_does_not_refresh(monkeypatch):
    story = _story()
    refreshed = []
    monkeypatch.setattr("core.service.story.refresh_misp_auto_update_jobs", refreshed.append)

    response, status = StoryService.ungroup_news_items([story.news_items[0].id], actor="bot")

    assert status == 200
    assert response["new_stories_ids"] == []
    assert refreshed == []


@pytest.mark.usefixtures("session")
def test_only_misp_update_path_skips_autosync(monkeypatch):
    scheduled = []
    monkeypatch.setattr("core.service.misp_auto_update.refresh_misp_auto_update_job", scheduled.append)
    story = _story()

    Story.update(story.id, {"title": "MISP update"}, external=True, actor="connector_misp")

    assert scheduled == []


@pytest.mark.usefixtures("session")
def test_invalid_auto_update_does_not_apply_other_story_changes(client, auth_header, monkeypatch):
    monkeypatch.setattr("core.service.misp_auto_update.refresh_misp_auto_update_job", lambda story_id: None)
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
def test_auto_update_proposals_are_stored_on_the_story(admin_user, monkeypatch):
    monkeypatch.setattr("core.service.misp_auto_update.refresh_misp_auto_update_job", lambda story_id: None)
    story = _story()
    connector = _misp_connector("MISP")
    Story.update(story.id, {"misp_auto_update": {"connector_id": connector.id, "enabled": True}}, admin_user)
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
    assert story.find_attribute_by_key("has_proposals").value == proposal_url

    assert apply_misp_sync_story_result(
        payload,
        clear_auto_update_proposals=True,
        proposal_url=proposal_url,
    )
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


@pytest.mark.usefixtures("session")
def test_handle_misp_connector_result_stores_blocked_auto_update_proposal():
    story = _story()
    proposal_url = "https://misp.example/events/view/event-1"

    handle_misp_connector_result(
        {
            "connector_type": "MISP_CONNECTOR",
            "connector_id": "connector-1",
            "sync_results": [{"type": "misp_auto_update_blocked", "story_id": story.id, "proposal_url": proposal_url}],
        }
    )

    assert story.find_attribute_by_key("has_proposals").value == proposal_url


@pytest.mark.usefixtures("session")
def test_handle_misp_connector_result_only_clears_matching_auto_update_proposal():
    story = _story()
    proposal_url = "https://misp.example/events/view/event-1"
    story.patch_attributes([{"key": "has_proposals", "value": proposal_url}])
    db.session.commit()
    payload = {
        "type": "misp_sync_story",
        "story_id": story.id,
        "misp_event_uuid": "event-1",
        "news_item_ids_to_mark_external": [],
        "auto_update": False,
        "proposal_url": proposal_url,
    }
    result = {"connector_type": "MISP_CONNECTOR", "connector_id": "connector-1", "sync_results": [payload]}

    handle_misp_connector_result(result)
    assert story.find_attribute_by_key("has_proposals").value == proposal_url

    payload.update(auto_update=True, proposal_url="https://misp.example/events/view/event-2")
    handle_misp_connector_result(result)
    assert story.find_attribute_by_key("has_proposals").value == proposal_url

    payload["proposal_url"] = proposal_url
    handle_misp_connector_result(result)
    assert story.find_attribute_by_key("has_proposals") is None


@pytest.mark.usefixtures("session")
def test_report_changes_refresh_affected_story_after_commit(admin_user, monkeypatch):
    refreshed = []
    monkeypatch.setattr("core.service.misp_auto_update.refresh_misp_auto_update_job", refreshed.append)
    story = _story()
    report_type = ReportItemType.get_all_for_collector()[0]

    report, status = ReportItem.add(
        {"title": "Report", "report_item_type_id": report_type.id, "stories": [story.id]},
        admin_user,
    )
    assert status == 200
    assert isinstance(report, ReportItem)
    assert refreshed == [story.id]

    refreshed.clear()
    assert ReportItem.update_report_item(report.id, {"title": "Renamed report"}, admin_user)[1] == 200
    assert refreshed == [story.id]

    refreshed.clear()
    assert ReportItem.set_stories(report.id, [], admin_user)[1] == 200
    assert refreshed == [story.id]

    refreshed.clear()
    assert ReportItem.add_stories(report.id, [story.id], admin_user)[1] == 200
    assert refreshed == [story.id]

    refreshed.clear()
    assert ReportItem.delete(report.id)[1] == 200
    assert refreshed == [story.id]


@pytest.mark.usefixtures("session")
def test_tag_deletion_refreshes_each_affected_story_once(monkeypatch):
    first_story = _story()
    second_story = _story()
    assert first_story.news_items[0].set_tags(["shared", "other"])[1] == 200
    assert second_story.news_items[0].set_tags(["shared"])[1] == 200
    refreshed = []
    monkeypatch.setattr("core.service.misp_auto_update.refresh_misp_auto_update_job", refreshed.append)

    NewsItemTagService.delete_tags_by_name("shared")
    assert set(refreshed) == {first_story.id, second_story.id}
    assert len(refreshed) == 2

    refreshed.clear()
    assert first_story.news_items[0].set_tags(["one", "two"])[1] == 200
    assert second_story.news_items[0].set_tags(["two"])[1] == 200
    assert NewsItemTagService.delete_all()[1] == 200
    assert set(refreshed) == {first_story.id, second_story.id}
    assert len(refreshed) == 2


@pytest.mark.usefixtures("session")
def test_connector_deletion_cancels_configured_story_jobs(admin_user, monkeypatch):
    story = _story()
    connector = _misp_connector("MISP")
    assert Story.update(story.id, {"misp_auto_update": {"connector_id": connector.id, "enabled": True}}, admin_user)[1] == 200
    cancelled = []
    monkeypatch.setattr("core.service.misp_auto_update.cancel_misp_auto_update_jobs", cancelled.append)

    assert Connector.delete(connector.id)[1] == 200

    assert cancelled == [[story.id]]


@pytest.mark.usefixtures("session")
def test_administrative_story_deletion_cancels_jobs(monkeypatch):
    story = _story()
    cancelled = []
    monkeypatch.setattr("core.service.story.cancel_misp_auto_update_jobs", cancelled.extend)

    assert StoryService.delete_all()[1] == 200

    assert story.id in cancelled


@pytest.mark.usefixtures("session")
def test_forced_source_deletion_refreshes_survivors_and_cancels_deleted_stories(monkeypatch):
    from core.model.osint_source import OSINTSource

    source = create_osint_source(rank=0)
    manual_source = OSINTSource.get_manual()
    deleted_story = create_story(news_items=[build_news_item_payload(source.id)])
    surviving_story = create_story(news_items=[build_news_item_payload(source.id), build_news_item_payload(manual_source.id)])
    deleted_story_id = deleted_story.id
    surviving_story_id = surviving_story.id
    refreshed = []
    cancelled = []
    monkeypatch.setattr("core.service.misp_auto_update.refresh_misp_auto_update_jobs", refreshed.extend)
    monkeypatch.setattr("core.service.story.cancel_misp_auto_update_jobs", cancelled.extend)

    assert OSINTSource.delete(source.id, force=True)[1] == 200

    assert Story.get(deleted_story_id) is None
    assert Story.get(surviving_story_id) is not None
    assert refreshed == [surviving_story_id]
    assert deleted_story_id in cancelled

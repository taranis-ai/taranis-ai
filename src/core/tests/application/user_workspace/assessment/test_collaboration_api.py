from datetime import datetime, timedelta

import pytest

from core.model.collaboration_channel import CollaborationChannelRecord
from core.service.collaboration import collaboration_service


@pytest.fixture(autouse=True)
def _clear_collaboration_state(app):
    with app.app_context():
        collaboration_service.channels.clear()
        collaboration_service._persistence_disabled_reason = None
        CollaborationChannelRecord.delete_all()
        yield
        collaboration_service.channels.clear()
        collaboration_service._persistence_disabled_reason = None
        CollaborationChannelRecord.delete_all()


def test_create_collaboration_channel_from_story(client, auth_header, stories):
    response = client.post(
        "/api/assess/collab/channels",
        json={"topic": "Demo Topic", "story_ids": [stories[0]]},
        headers=auth_header,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["topic"] == "Demo Topic"
    assert payload["status"] == "open"
    assert payload["invite"]["owner_base_url"] == collaboration_service.external_base_url()
    assert payload["invite"]["join_url"].endswith(f"channel_id={payload['channel_id']}&token={payload['invite']['token']}")
    assert payload["workspace"]["active_mode"] == "story"
    assert len(payload["stories"]) == 1
    assert payload["stories"][0]["source_story_id"] == stories[0]


def test_collaboration_channel_invite_can_be_redeemed_multiple_times(client, auth_header, stories):
    create_response = client.post(
        "/api/assess/collab/channels",
        json={"topic": "Shared Topic", "story_ids": [stories[0]]},
        headers=auth_header,
    )
    payload = create_response.get_json()
    channel_id = payload["channel_id"]
    token = payload["invite"]["token"]

    join_a = client.post(
        f"/api/assess/collab/channels/{channel_id}/join",
        json={"token": token, "partner_base_url": "https://bravo.demo"},
    )
    join_b = client.post(
        f"/api/assess/collab/channels/{channel_id}/join",
        json={"token": token, "partner_base_url": "https://charlie.demo"},
    )

    assert join_a.status_code == 200
    assert join_b.status_code == 200
    participants = join_b.get_json()["participants"]
    participant_urls = {participant["base_url"] for participant in participants}
    assert {"https://bravo.demo", "https://charlie.demo", collaboration_service.external_base_url()} <= participant_urls


def test_collaboration_channel_list_is_sorted_by_creation_time(client, auth_header):
    first_token = collaboration_service._build_token("channel-1")
    second_token = collaboration_service._build_token("channel-2")
    collaboration_service.channels["channel-1"] = {
        "channel_id": "channel-1",
        "topic": "Older Channel",
        "status": "open",
        "token": first_token,
        "owner_base_url": collaboration_service.external_base_url(),
        "participants": [{"base_url": collaboration_service.external_base_url(), "role": "owner"}],
        "stories": [],
        "result_stories": [],
        "created_at": "2026-05-08T09:00:00",
        "updated_at": "2026-06-22T11:00:00",
    }
    collaboration_service.channels["channel-2"] = {
        "channel_id": "channel-2",
        "topic": "Newer Channel",
        "status": "open",
        "token": second_token,
        "owner_base_url": collaboration_service.external_base_url(),
        "participants": [{"base_url": collaboration_service.external_base_url(), "role": "owner"}],
        "stories": [],
        "result_stories": [],
        "created_at": "2026-05-08T10:00:00",
        "updated_at": "2026-05-08T10:05:00",
    }

    response = client.get("/api/assess/collab/channels", headers=auth_header)

    assert response.status_code == 200
    payload = response.get_json()
    assert [item["channel_id"] for item in payload["items"]] == ["channel-2", "channel-1"]


def test_finalize_collaboration_channel_creates_local_stories_for_remote_origin(client, auth_header, stories):
    create_response = client.post(
        "/api/assess/collab/channels",
        json={"topic": "Finalize Topic", "story_ids": [stories[0]]},
        headers=auth_header,
    )
    channel_id = create_response.get_json()["channel_id"]
    snapshot = collaboration_service.channels[channel_id]["result_stories"][0]
    snapshot["source_instance"] = "https://remote.demo"
    snapshot["source_story_id"] = "remote-story-1"
    snapshot["persisted_local_story_id"] = None

    finalize_response = client.post(f"/api/assess/collab/channels/{channel_id}/finalize", json={}, headers=auth_header)

    assert finalize_response.status_code == 200
    payload = finalize_response.get_json()
    assert payload["channel_id"] == channel_id
    assert payload["created_story_ids"]
    created_story_id = payload["created_story_ids"][0]
    assert payload["persisted_story_ids"] == payload["report_story_ids"]

    story_response = client.get(f"/api/assess/story/{created_story_id}", headers=auth_header)
    assert story_response.status_code == 200


def test_finalize_collaboration_channel_updates_local_origin_story_in_place(client, auth_header, stories):
    create_response = client.post(
        "/api/assess/collab/channels",
        json={"topic": "Finalize Local Update", "story_ids": [stories[0]]},
        headers=auth_header,
    )
    channel_id = create_response.get_json()["channel_id"]
    snapshot = collaboration_service.channels[channel_id]["result_stories"][0]
    snapshot["story"]["summary"] = "Updated through collaboration finalize"

    finalize_response = client.post(f"/api/assess/collab/channels/{channel_id}/finalize", json={}, headers=auth_header)

    assert finalize_response.status_code == 200
    payload = finalize_response.get_json()
    assert payload["created_story_ids"] == []
    assert payload["updated_story_ids"] == [stories[0]]
    assert payload["report_story_ids"] == [stories[0]]

    story_response = client.get(f"/api/assess/story/{stories[0]}", headers=auth_header)
    assert story_response.status_code == 200
    assert story_response.get_json()["summary"] == "Updated through collaboration finalize"


def test_finalize_collaboration_channel_reuses_remote_persisted_story(client, auth_header, stories):
    create_response = client.post(
        "/api/assess/collab/channels",
        json={"topic": "Finalize Remote Update", "story_ids": [stories[0]]},
        headers=auth_header,
    )
    channel_id = create_response.get_json()["channel_id"]
    snapshot = collaboration_service.channels[channel_id]["result_stories"][0]
    snapshot["source_instance"] = "https://remote.demo"
    snapshot["source_story_id"] = "remote-story-1"
    snapshot["persisted_local_story_id"] = None

    first_finalize = client.post(f"/api/assess/collab/channels/{channel_id}/finalize", json={}, headers=auth_header)

    assert first_finalize.status_code == 200
    first_payload = first_finalize.get_json()
    assert len(first_payload["created_story_ids"]) == 1
    created_story_id = first_payload["created_story_ids"][0]

    snapshot["story"]["summary"] = "Updated after first persistence"
    second_finalize = client.post(f"/api/assess/collab/channels/{channel_id}/finalize", json={}, headers=auth_header)

    assert second_finalize.status_code == 200
    second_payload = second_finalize.get_json()
    assert second_payload["created_story_ids"] == []
    assert second_payload["updated_story_ids"] == [created_story_id]
    assert second_payload["report_story_ids"] == [created_story_id]

    story_response = client.get(f"/api/assess/story/{created_story_id}", headers=auth_header)
    assert story_response.status_code == 200
    assert story_response.get_json()["summary"] == "Updated after first persistence"


def test_collaboration_live_state_tracks_presence_and_locks(client, auth_header, stories):
    create_response = client.post(
        "/api/assess/collab/channels",
        json={"topic": "Live Topic", "story_ids": [stories[0]]},
        headers=auth_header,
    )
    payload = create_response.get_json()
    channel_id = payload["channel_id"]
    snapshot_id = payload["stories"][0]["id"]
    actor = {
        "base_url": collaboration_service.external_base_url(),
        "session_id": "session-a",
        "username": "alice",
    }

    detail = collaboration_service.register_presence(
        channel_id, participant_base_url=actor["base_url"], session_id="session-a", username="alice"
    )
    detail = collaboration_service.acquire_field_lock(
        channel_id,
        snapshot_id=snapshot_id,
        field_name="summary",
        participant_base_url=actor["base_url"],
        session_id="session-a",
        username="alice",
        selected_story_id=snapshot_id,
    )

    assert detail.presence[0].username == "alice"
    assert detail.locks[0].field_name == "summary"

    response = client.get(f"/api/assess/collab/channels/{channel_id}/live-state", headers=auth_header)
    assert response.status_code == 200
    live_payload = response.get_json()
    assert live_payload["presence"][0]["username"] == "alice"
    assert live_payload["locks"][0]["field_name"] == "summary"


def test_collaboration_live_lock_blocks_other_session(client, auth_header, stories):
    create_response = client.post(
        "/api/assess/collab/channels",
        json={"topic": "Live Locks", "story_ids": [stories[0]]},
        headers=auth_header,
    )
    payload = create_response.get_json()
    channel_id = payload["channel_id"]
    snapshot_id = payload["stories"][0]["id"]
    base_url = collaboration_service.external_base_url()

    collaboration_service.acquire_field_lock(
        channel_id,
        snapshot_id=snapshot_id,
        field_name="summary",
        participant_base_url=base_url,
        session_id="session-a",
        username="alice",
        selected_story_id=snapshot_id,
    )

    with pytest.raises(PermissionError):
        collaboration_service.update_story_snapshot_live(
            channel_id,
            snapshot_id,
            {"summary": "blocked"},
            participant_base_url=base_url,
            session_id="session-b",
            username="bob",
            selected_story_id=snapshot_id,
        )

    updated = collaboration_service.update_story_snapshot_live(
        channel_id,
        snapshot_id,
        {"summary": "allowed"},
        participant_base_url=base_url,
        session_id="session-a",
        username="alice",
        selected_story_id=snapshot_id,
    )

    assert updated.stories[0].story["summary"] == "allowed"


def test_collaboration_live_workspace_patch_updates_channel_state(client, auth_header, stories):
    create_response = client.post(
        "/api/assess/collab/channels",
        json={"topic": "Workspace Topic", "story_ids": [stories[0]]},
        headers=auth_header,
    )
    payload = create_response.get_json()
    channel_id = payload["channel_id"]
    actor = {
        "base_url": collaboration_service.external_base_url(),
        "session_id": "session-a",
        "username": "alice",
    }

    response = client.post(
        f"/api/assess/collab/channels/{channel_id}/live/workspace-patch",
        json={
            "target": "decision",
            "action": "upsert",
            "actor": actor,
            "data": {"text": "Publish TLP:AMBER advisory", "owner": "alice", "status": "open"},
        },
        headers=auth_header,
    )

    assert response.status_code == 200
    workspace_payload = response.get_json()["workspace"]
    assert workspace_payload["decisions"][0]["text"] == "Publish TLP:AMBER advisory"
    assert workspace_payload["activity_items"][0]["actor"] == "alice"
    assert workspace_payload["activity_items"][0]["participant_base_url"] == actor["base_url"]


def test_collaboration_live_chat_message_tracks_instance_metadata(client, auth_header, stories):
    create_response = client.post(
        "/api/assess/collab/channels",
        json={"topic": "Chat Topic", "story_ids": [stories[0]]},
        headers=auth_header,
    )
    channel_id = create_response.get_json()["channel_id"]
    actor = {
        "base_url": collaboration_service.external_base_url(),
        "session_id": "session-a",
        "username": "alice",
    }

    response = client.post(
        f"/api/assess/collab/channels/{channel_id}/live/workspace-patch",
        json={
            "target": "chat_message",
            "action": "upsert",
            "actor": actor,
            "data": {"text": "Need eyes on this summary"},
        },
        headers=auth_header,
    )

    assert response.status_code == 200
    workspace_payload = response.get_json()["workspace"]
    assert workspace_payload["chat_messages"][0]["author"] == "alice"
    assert workspace_payload["chat_messages"][0]["participant_base_url"] == actor["base_url"]
    assert workspace_payload["chat_messages"][0]["participant_short_name"]
    assert workspace_payload["activity_items"][0]["participant_short_name"] == workspace_payload["chat_messages"][0]["participant_short_name"]


def test_collaboration_live_task_and_comment_track_instance_metadata(client, auth_header, stories):
    create_response = client.post(
        "/api/assess/collab/channels",
        json={"topic": "Metadata Topic", "story_ids": [stories[0]]},
        headers=auth_header,
    )
    channel_id = create_response.get_json()["channel_id"]
    actor = {
        "base_url": collaboration_service.external_base_url(),
        "session_id": "session-a",
        "username": "alice",
    }

    task_response = client.post(
        f"/api/assess/collab/channels/{channel_id}/live/workspace-patch",
        json={
            "target": "task",
            "action": "upsert",
            "actor": actor,
            "data": {"text": "Verify indicators", "status": "todo"},
        },
        headers=auth_header,
    )
    comment_response = client.post(
        f"/api/assess/collab/channels/{channel_id}/live/workspace-patch",
        json={
            "target": "comment",
            "action": "upsert",
            "actor": actor,
            "data": {"text": "Initial partner note"},
        },
        headers=auth_header,
    )

    assert task_response.status_code == 200
    assert comment_response.status_code == 200

    task_payload = task_response.get_json()["workspace"]["tasks"][0]
    comment_payload = comment_response.get_json()["workspace"]["comments"][0]
    assert task_payload["owner"] == "alice"
    assert task_payload["participant_base_url"] == actor["base_url"]
    assert task_payload["participant_short_name"]
    assert comment_payload["author"] == "alice"
    assert comment_payload["participant_base_url"] == actor["base_url"]
    assert comment_payload["participant_short_name"]


def test_collaboration_story_ops_merge_concurrent_updates(client, auth_header, stories):
    create_response = client.post(
        "/api/assess/collab/channels",
        json={"topic": "Ops Topic", "story_ids": [stories[0]]},
        headers=auth_header,
    )
    payload = create_response.get_json()
    channel_id = payload["channel_id"]
    snapshot_id = payload["stories"][0]["id"]
    base_url = collaboration_service.external_base_url()

    first_detail, first_applied = collaboration_service.submit_story_ops_live(
        channel_id,
        snapshot_id=snapshot_id,
        field_name="summary",
        version=0,
        op_id="op-a",
        updates=[{"from": 0, "to": 0, "insert": "Alpha "}],
        participant_base_url=base_url,
        session_id="session-a",
        username="alice",
    )
    second_detail, second_applied = collaboration_service.submit_story_ops_live(
        channel_id,
        snapshot_id=snapshot_id,
        field_name="summary",
        version=0,
        op_id="op-b",
        updates=[{"from": 0, "to": 0, "insert": "Bravo "}],
        participant_base_url=base_url,
        session_id="session-b",
        username="bob",
    )

    assert first_applied["version"] == 1
    assert second_applied["version"] == 2
    summary_doc = next(doc for doc in second_detail.shared_docs if doc.snapshot_id == snapshot_id and doc.field_name == "summary")
    assert summary_doc.version == 2
    assert second_detail.stories[0].story["summary"] == "Alpha Bravo " or second_detail.stories[0].story["summary"] == "Bravo Alpha "
    assert second_detail.stories[0].story["summary"] == summary_doc.text
    first_summary_doc = next(doc for doc in first_detail.shared_docs if doc.snapshot_id == snapshot_id and doc.field_name == "summary")
    assert first_summary_doc.text == "Alpha "


def test_collaboration_story_ops_rebase_stale_version(client, auth_header, stories):
    create_response = client.post(
        "/api/assess/collab/channels",
        json={"topic": "Rebase Topic", "story_ids": [stories[0]]},
        headers=auth_header,
    )
    payload = create_response.get_json()
    channel_id = payload["channel_id"]
    snapshot_id = payload["stories"][0]["id"]
    base_url = collaboration_service.external_base_url()

    collaboration_service.submit_story_ops_live(
        channel_id,
        snapshot_id=snapshot_id,
        field_name="title",
        version=0,
        op_id="title-1",
        updates=[{"from": 0, "to": 0, "insert": "First "}],
        participant_base_url=base_url,
        session_id="session-a",
        username="alice",
    )
    detail, applied = collaboration_service.submit_story_ops_live(
        channel_id,
        snapshot_id=snapshot_id,
        field_name="title",
        version=0,
        op_id="title-2",
        updates=[{"from": 0, "to": 0, "insert": "Second "}],
        participant_base_url=base_url,
        session_id="session-b",
        username="bob",
    )

    assert applied["version"] == 2
    assert detail.stories[0].story["title"].startswith("First Second ") or detail.stories[0].story["title"].startswith("Second First ")
    assert any(doc.field_name == "title" and doc.version == 2 for doc in detail.shared_docs)


def test_collaboration_text_selection_lifecycle(client, auth_header, stories):
    create_response = client.post(
        "/api/assess/collab/channels",
        json={"topic": "Selection Topic", "story_ids": [stories[0]]},
        headers=auth_header,
    )
    payload = create_response.get_json()
    channel_id = payload["channel_id"]
    snapshot_id = payload["stories"][0]["id"]
    base_url = collaboration_service.external_base_url()

    detail, selection = collaboration_service.update_story_selection_live(
        channel_id,
        snapshot_id=snapshot_id,
        field_name="summary",
        anchor=2,
        head=5,
        participant_base_url=base_url,
        session_id="session-a",
        username="alice",
    )
    assert selection["anchor"] == 2
    assert detail.text_selections[0].field_name == "summary"

    detail, _ = collaboration_service.clear_story_selection_live(
        channel_id,
        snapshot_id=snapshot_id,
        field_name="summary",
        participant_base_url=base_url,
        session_id="session-a",
    )
    assert detail.text_selections == []

    collaboration_service.update_story_selection_live(
        channel_id,
        snapshot_id=snapshot_id,
        field_name="summary",
        anchor=1,
        head=1,
        participant_base_url=base_url,
        session_id="session-a",
        username="alice",
    )
    detail = collaboration_service.unregister_presence(channel_id, "session-a", active_instance_base_url=base_url)
    assert detail.text_selections == []


def test_closed_collaboration_channel_survives_in_memory_reset(client, auth_header, stories):
    create_response = client.post(
        "/api/assess/collab/channels",
        json={"topic": "Archived Topic", "story_ids": [stories[0]]},
        headers=auth_header,
    )
    channel_id = create_response.get_json()["channel_id"]

    close_response = client.post(f"/api/assess/collab/channels/{channel_id}/close", headers=auth_header)

    assert close_response.status_code == 200

    collaboration_service.channels.clear()

    list_response = client.get("/api/assess/collab/channels", headers=auth_header)
    detail_response = client.get(f"/api/assess/collab/channels/{channel_id}", headers=auth_header)

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert [item["channel_id"] for item in list_response.get_json()["items"]] == [channel_id]
    assert list_response.get_json()["items"][0]["status"] == "closed"
    assert detail_response.get_json()["channel_id"] == channel_id
    assert detail_response.get_json()["status"] == "closed"


def test_collaboration_live_mutations_are_debounced_until_interval_elapsed(client, auth_header, stories, monkeypatch):
    create_response = client.post(
        "/api/assess/collab/channels",
        json={"topic": "Debounce Topic", "story_ids": [stories[0]]},
        headers=auth_header,
    )
    channel_id = create_response.get_json()["channel_id"]
    channel_state = collaboration_service.channels[channel_id]
    channel_state["_last_persisted_at"] = datetime(2026, 7, 1, 10, 0, 0).isoformat()

    persisted_states: list[dict] = []
    original_upsert = CollaborationChannelRecord.upsert_state

    def spy_upsert(channel_payload):
        persisted_states.append(channel_payload)
        return original_upsert(channel_payload)

    monkeypatch.setattr("core.service.collaboration.CollaborationChannelRecord.upsert_state", spy_upsert)
    monkeypatch.setattr("core.service.collaboration._utcnow", lambda: datetime(2026, 7, 1, 10, 1, 0))

    first_response = client.post(
        f"/api/assess/collab/channels/{channel_id}/live/workspace-patch",
        json={
            "target": "chat_message",
            "action": "upsert",
            "actor": {"base_url": collaboration_service.external_base_url(), "session_id": "session-a", "username": "alice"},
            "data": {"text": "not yet persisted"},
        },
        headers=auth_header,
    )

    assert first_response.status_code == 200
    assert persisted_states == []

    monkeypatch.setattr("core.service.collaboration._utcnow", lambda: datetime(2026, 7, 1, 10, 3, 0))

    second_response = client.post(
        f"/api/assess/collab/channels/{channel_id}/live/workspace-patch",
        json={
            "target": "chat_message",
            "action": "upsert",
            "actor": {"base_url": collaboration_service.external_base_url(), "session_id": "session-a", "username": "alice"},
            "data": {"text": "persist now"},
        },
        headers=auth_header,
    )

    assert second_response.status_code == 200
    assert len(persisted_states) == 1
    assert persisted_states[0]["workspace"]["chat_messages"][0]["text"] == "persist now"


def test_collaboration_open_channel_persistence_excludes_ephemeral_runtime_state(client, auth_header, stories, monkeypatch):
    create_response = client.post(
        "/api/assess/collab/channels",
        json={"topic": "Ephemeral Topic", "story_ids": [stories[0]]},
        headers=auth_header,
    )
    payload = create_response.get_json()
    channel_id = payload["channel_id"]
    snapshot_id = payload["stories"][0]["id"]
    base_url = collaboration_service.external_base_url()

    collaboration_service.register_presence(channel_id, participant_base_url=base_url, session_id="session-a", username="alice")
    collaboration_service.acquire_field_lock(
        channel_id,
        snapshot_id=snapshot_id,
        field_name="summary",
        participant_base_url=base_url,
        session_id="session-a",
        username="alice",
        selected_story_id=snapshot_id,
    )
    collaboration_service.update_story_selection_live(
        channel_id,
        snapshot_id=snapshot_id,
        field_name="summary",
        anchor=1,
        head=3,
        participant_base_url=base_url,
        session_id="session-a",
        username="alice",
    )

    collaboration_service.channels[channel_id]["_last_persisted_at"] = datetime(2026, 7, 1, 10, 0, 0).isoformat()
    monkeypatch.setattr("core.service.collaboration._utcnow", lambda: datetime(2026, 7, 1, 10, 3, 0))

    workspace_response = client.post(
        f"/api/assess/collab/channels/{channel_id}/live/workspace-patch",
        json={
            "target": "chat_message",
            "action": "upsert",
            "actor": {"base_url": base_url, "session_id": "session-a", "username": "alice"},
            "data": {"text": "persist durable only"},
        },
        headers=auth_header,
    )

    assert workspace_response.status_code == 200

    record = CollaborationChannelRecord.get(channel_id)
    assert record is not None
    assert record.state["runtime"]["presence"] == []
    assert record.state["runtime"]["locks"] == []
    assert record.state["runtime"]["text_selections"] == {}

    collaboration_service.channels.clear()

    reloaded = collaboration_service.get_channel(channel_id, active_instance_base_url=base_url)
    assert reloaded.presence == []
    assert reloaded.locks == []
    assert reloaded.text_selections == []
    assert reloaded.workspace.chat_messages[0].text == "persist durable only"


def test_collaboration_close_forces_immediate_persistence(client, auth_header, stories, monkeypatch):
    create_response = client.post(
        "/api/assess/collab/channels",
        json={"topic": "Close Topic", "story_ids": [stories[0]]},
        headers=auth_header,
    )
    channel_id = create_response.get_json()["channel_id"]
    collaboration_service.channels[channel_id]["_last_persisted_at"] = datetime(2026, 7, 1, 10, 0, 0).isoformat()

    persisted_states: list[dict] = []
    original_upsert = CollaborationChannelRecord.upsert_state

    def spy_upsert(channel_payload):
        persisted_states.append(channel_payload)
        return original_upsert(channel_payload)

    monkeypatch.setattr("core.service.collaboration.CollaborationChannelRecord.upsert_state", spy_upsert)
    monkeypatch.setattr("core.service.collaboration._utcnow", lambda: datetime(2026, 7, 1, 10, 0, 30))

    detail = collaboration_service.close_channel(channel_id)

    assert detail.status == "closed"
    assert len(persisted_states) == 1
    assert persisted_states[0]["status"] == "closed"


def test_collaboration_live_workspace_patch_still_works_when_persistence_is_unavailable(client, auth_header, stories, monkeypatch):
    create_response = client.post(
        "/api/assess/collab/channels",
        json={"topic": "Fallback Topic", "story_ids": [stories[0]]},
        headers=auth_header,
    )
    channel_id = create_response.get_json()["channel_id"]
    collaboration_service.channels[channel_id]["_last_persisted_at"] = (datetime(2026, 7, 1, 10, 0, 0) - timedelta(minutes=3)).isoformat()
    actor = {
        "base_url": collaboration_service.external_base_url(),
        "session_id": "session-a",
        "username": "alice",
    }
    monkeypatch.setattr("core.service.collaboration._utcnow", lambda: datetime(2026, 7, 1, 10, 0, 0))

    monkeypatch.setattr(
        "core.service.collaboration.CollaborationChannelRecord.upsert_state",
        lambda _channel_state: (_ for _ in ()).throw(RuntimeError("persistence unavailable")),
    )

    response = client.post(
        f"/api/assess/collab/channels/{channel_id}/live/workspace-patch",
        json={
            "target": "chat_message",
            "action": "upsert",
            "actor": actor,
            "data": {"text": "Still works"},
        },
        headers=auth_header,
    )

    assert response.status_code == 200
    workspace_payload = response.get_json()["workspace"]
    assert workspace_payload["chat_messages"][0]["text"] == "Still works"
    assert collaboration_service._persistence_disabled_reason == "persistence unavailable"

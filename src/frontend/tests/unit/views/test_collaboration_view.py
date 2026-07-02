import json

from frontend.config import Config


def test_collaboration_dialog_renders_open_channels(authenticated_client, responses_mock):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/collab/channels",
        json={
            "items": [
                {
                    "channel_id": "channel-1",
                    "topic": "Demo Topic",
                    "status": "open",
                    "owner_base_url": "https://alpha.demo",
                    "story_count": 2,
                    "participant_count": 3,
                    "created_at": "2026-05-08T10:00:00",
                    "updated_at": "2026-05-08T10:00:00",
                    "invite": {
                        "owner_base_url": "https://alpha.demo",
                        "channel_id": "channel-1",
                        "token": "token-1",
                        "join_url": "/collaboration/join?channel_id=channel-1",
                    },
                }
            ],
            "total_count": 1,
        },
    )

    with authenticated_client.session_transaction() as flask_session:
        flask_session["collab_current_channel"] = "channel-1"

    response = authenticated_client.get("/collaboration/dialog?story_id=story-1")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Demo Topic" in html
    assert 'name="story_ids" value="story-1"' in html
    assert "Choose an open channel for these stories, or create a new one." in html
    assert "How do you want to continue?" in html
    assert 'value="Existing channel"' in html
    assert 'value="New channel"' in html
    assert "x-show=" in html
    assert "mode === 'existing'" in html
    assert "mode === 'new'" in html
    assert "Open channel" in html
    assert "New channel name" in html
    assert "Demo Topic &bull; 2 stories" in html
    assert "Pick one of the open channels." in html
    assert "Choose a short name others will recognize." in html
    assert ":name=\"mode === 'existing' ? 'channel_id' : null\"" in html
    assert ":name=\"mode === 'new' ? 'topic' : null\"" in html
    assert '"existing"' in html


def test_collaboration_dialog_without_story_ids_supports_new_channel(authenticated_client, responses_mock):
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assess/collab/channels", json={"items": [], "total_count": 0})

    response = authenticated_client.get("/collaboration/dialog")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Create a collaboration channel to start a new topic." in html
    assert "Stories are not being added in this step. After the channel is created, add stories from Assess." in html
    assert "How do you want to continue?" not in html
    assert "Open channel" not in html
    assert "New channel name" in html


def test_collaboration_dialog_force_new_clears_current_channel_selection(authenticated_client, responses_mock):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/collab/channels",
        json={
            "items": [
                {
                    "channel_id": "channel-1",
                    "topic": "Demo Topic",
                    "status": "open",
                    "owner_base_url": "https://alpha.demo",
                    "story_count": 2,
                    "participant_count": 3,
                    "created_at": "2026-05-08T10:00:00",
                    "updated_at": "2026-05-08T10:00:00",
                    "invite": {
                        "owner_base_url": "https://alpha.demo",
                        "channel_id": "channel-1",
                        "token": "token-1",
                        "join_url": "/collaboration/join?channel_id=channel-1",
                    },
                }
            ],
            "total_count": 1,
        },
    )

    with authenticated_client.session_transaction() as flask_session:
        flask_session["collab_current_channel"] = "channel-1"

    response = authenticated_client.get("/collaboration/dialog?force_new=1")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'option value="channel-1" selected' not in html
    assert '"new"' in html


def test_collaboration_dialog_with_open_channels_and_force_new_shows_new_channel_as_primary_section(authenticated_client, responses_mock):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/collab/channels",
        json={
            "items": [
                {
                    "channel_id": "channel-1",
                    "topic": "Demo Topic",
                    "status": "open",
                    "owner_base_url": "https://alpha.demo",
                    "story_count": 2,
                    "participant_count": 3,
                    "created_at": "2026-05-08T10:00:00",
                    "updated_at": "2026-05-08T10:00:00",
                    "invite": {
                        "owner_base_url": "https://alpha.demo",
                        "channel_id": "channel-1",
                        "token": "token-1",
                        "join_url": "/collaboration/join?channel_id=channel-1",
                    },
                }
            ],
            "total_count": 1,
        },
    )

    response = authenticated_client.get("/collaboration/dialog?story_id=story-1&force_new=1&topic=Fresh%20Topic")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert '"new"' in html
    assert ":name=\"mode === 'new' ? 'topic' : null\"" in html
    assert 'value="Fresh Topic"' in html
    assert "New channel name" in html


def test_collaboration_dialog_without_open_channels_only_supports_new_channel(authenticated_client, responses_mock):
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assess/collab/channels", json={"items": [], "total_count": 0})

    response = authenticated_client.get("/collaboration/dialog?story_id=story-1")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Choose an open channel for these stories, or create a new one." in html
    assert "How do you want to continue?" not in html
    assert "Open channel" not in html
    assert "New channel name" in html
    assert 'name="story_ids" value="story-1"' in html


def test_collaboration_dialog_submit_creates_new_channel_from_workspace(authenticated_client, responses_mock):
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/assess/collab/channels",
        json={"channel_id": "channel-2"},
    )

    response = authenticated_client.post(
        "/collaboration/dialog",
        data={"topic": "Fresh Topic"},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 204
    assert response.headers["HX-Redirect"].endswith("/collaboration?channel_id=channel-2")
    request_body = json.loads(responses_mock.calls[0].request.body)
    assert request_body == {"topic": "Fresh Topic", "story_ids": []}


def test_collaboration_dialog_submit_creates_new_channel_with_plain_redirect(authenticated_client, responses_mock):
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/assess/collab/channels",
        json={"channel_id": "channel-2"},
    )

    response = authenticated_client.post(
        "/collaboration/dialog",
        data={"topic": "Fresh Topic"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/collaboration?channel_id=channel-2")


def test_collaboration_dialog_submit_creates_story_backed_channel_into_room(authenticated_client, responses_mock):
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/assess/collab/channels",
        json={"channel_id": "channel-2"},
    )

    response = authenticated_client.post(
        "/collaboration/dialog",
        data={"topic": "Fresh Topic", "story_ids": ["story-1"]},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 204
    assert response.headers["HX-Redirect"].endswith("/collaboration/channel-2")


def test_collaboration_close_redirects_to_closed_channel_archive(authenticated_client, responses_mock):
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/assess/collab/channels/channel-1/close",
        json={"channel_id": "channel-1", "status": "closed"},
    )

    with authenticated_client.session_transaction() as flask_session:
        flask_session["collab_channels"] = ["channel-1", "channel-2"]
        flask_session["collab_current_channel"] = "channel-1"

    response = authenticated_client.post("/collaboration/channel-1/close", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/collaboration?channel_id=channel-1")


def test_collaboration_close_last_channel_redirects_to_closed_channel_archive(authenticated_client, responses_mock):
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/assess/collab/channels/channel-1/close",
        json={"channel_id": "channel-1", "status": "closed"},
    )

    with authenticated_client.session_transaction() as flask_session:
        flask_session["collab_channels"] = ["channel-1"]
        flask_session["collab_current_channel"] = "channel-1"

    response = authenticated_client.post("/collaboration/channel-1/close", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/collaboration?channel_id=channel-1")


def test_collaboration_workspace_renders_active_channel(authenticated_client, responses_mock):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/collab/channels",
        json={
            "items": [
                {
                    "channel_id": "channel-1",
                    "topic": "Live Demo",
                    "status": "open",
                    "owner_base_url": "https://alpha.demo",
                    "story_count": 1,
                    "participant_count": 2,
                    "created_at": "2026-05-08T10:00:00",
                    "updated_at": "2026-05-08T10:00:00",
                    "invite": {
                        "owner_base_url": "https://alpha.demo",
                        "channel_id": "channel-1",
                        "token": "token-1",
                        "join_url": "/collaboration/join?channel_id=channel-1",
                    },
                }
            ],
            "total_count": 1,
        },
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/collab/channels/channel-1",
        json={
            "channel_id": "channel-1",
            "topic": "Live Demo",
            "status": "open",
            "owner_base_url": "https://alpha.demo",
            "active_instance_base_url": "https://alpha.demo",
            "invite": {
                "owner_base_url": "https://alpha.demo",
                "channel_id": "channel-1",
                "token": "token-1",
                "join_url": "/collaboration/join?channel_id=channel-1",
            },
            "participants": [
                {"base_url": "https://alpha.demo", "role": "owner", "joined_at": "2026-05-08T10:00:00"},
                {"base_url": "https://bravo.demo", "role": "participant", "joined_at": "2026-05-08T10:01:00"},
            ],
            "presence": [
                {
                    "session_id": "session-1",
                    "participant_base_url": "https://bravo.demo",
                    "username": "bravo-user",
                    "connected_at": "2026-05-08T10:01:00",
                    "last_seen_at": "2026-05-08T10:01:05",
                    "selected_story_id": "snapshot-1",
                }
            ],
            "locks": [],
            "workspace": {
                "focused_story_id": "snapshot-1",
                "active_mode": "story",
                "briefing": {
                    "impact": "High",
                    "key_takeaways": ["Takeaway"],
                    "risks": ["Risk"],
                    "key_questions": ["Question"],
                    "related_story_ids": [],
                    "source_labels": ["CERT-EU"],
                },
                "decisions": [],
                "tasks": [],
                "comments": [],
                "chat_messages": [],
                "timeline_events": [],
                "activity_items": [],
            },
            "stories": [
                {
                    "id": "snapshot-1",
                    "title": "Story in Channel",
                    "description": "Joined from assess",
                    "created": "2026-05-08T10:00:00",
                    "source_instance": "https://alpha.demo",
                    "source_story_id": "story-1",
                    "story": {"id": "story-1", "title": "Story in Channel", "summary": "Shared summary", "news_items": []},
                }
            ],
            "result_stories": [],
            "created_at": "2026-05-08T10:00:00",
            "updated_at": "2026-05-08T10:00:00",
            "is_owner": True,
        },
    )

    response = authenticated_client.get("/collaboration/channel-1")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Live Story Room" in html
    assert "Story in Channel" in html
    assert "https://bravo.demo" in html
    assert "data-collab-connection-status" in html
    assert "Live sync idle." in html
    assert "Add From Assess" in html
    assert ">Close<" in html
    assert "Open Live Room" not in html
    assert "New Channel" not in html
    assert "Channel Tasks" in html
    assert "Shared across all stories" in html
    assert "Open Original Story" not in html
    assert "Briefing Mode" not in html
    assert "Story Focus" not in html
    assert "vendor/codemirror.js" in html
    assert 'data-collab-editor-host="summary"' in html
    assert "Nobody here" in html
    assert html.count("data-collab-copy-link") == 0


def test_collaboration_overview_renders_dashboard_surface(authenticated_client, responses_mock):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/collab/channels",
        json={
            "items": [
                {
                    "channel_id": "channel-2",
                    "topic": "Second Channel",
                    "status": "open",
                    "owner_base_url": "https://bravo.demo",
                    "story_count": 3,
                    "participant_count": 4,
                    "created_at": "2026-05-08T09:00:00",
                    "updated_at": "2026-05-08T09:30:00",
                    "invite": {
                        "owner_base_url": "https://bravo.demo",
                        "channel_id": "channel-2",
                        "token": "token-2",
                        "join_url": "/collaboration/join?channel_id=channel-2",
                    },
                },
                {
                    "channel_id": "channel-1",
                    "topic": "Live Demo",
                    "status": "open",
                    "owner_base_url": "https://alpha.demo",
                    "story_count": 1,
                    "participant_count": 2,
                    "created_at": "2026-05-08T10:00:00",
                    "updated_at": "2026-05-08T10:00:00",
                    "invite": {
                        "owner_base_url": "https://alpha.demo",
                        "channel_id": "channel-1",
                        "token": "token-1",
                        "join_url": "/collaboration/join?channel_id=channel-1",
                    },
                },
            ],
            "total_count": 1,
        },
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/collab/channels/channel-1",
        json={
            "channel_id": "channel-1",
            "topic": "Live Demo",
            "status": "open",
            "owner_base_url": "https://alpha.demo",
            "active_instance_base_url": "https://alpha.demo",
            "invite": {
                "owner_base_url": "https://alpha.demo",
                "channel_id": "channel-1",
                "token": "token-1",
                "join_url": "/collaboration/join?channel_id=channel-1",
            },
            "participants": [{"base_url": "https://alpha.demo", "role": "owner", "joined_at": "2026-05-08T10:00:00"}],
            "presence": [],
            "locks": [],
            "workspace": {
                "focused_story_id": "snapshot-1",
                "active_mode": "briefing",
                "briefing": {
                    "impact": "High",
                    "key_takeaways": ["Takeaway"],
                    "risks": ["Risk"],
                    "key_questions": ["Question"],
                    "related_story_ids": [],
                    "source_labels": ["CERT-EU"],
                },
                "decisions": [],
                "tasks": [],
                "comments": [],
                "chat_messages": [],
                "timeline_events": [],
                "activity_items": [],
            },
            "stories": [
                {
                    "id": "snapshot-1",
                    "title": "Story in Channel",
                    "description": "Joined from assess",
                    "created": "2026-05-08T10:00:00",
                    "source_instance": "https://alpha.demo",
                    "source_story_id": "story-1",
                    "story": {"id": "story-1", "title": "Story in Channel", "summary": "Shared summary", "news_items": []},
                }
            ],
            "result_stories": [],
            "created_at": "2026-05-08T10:00:00",
            "updated_at": "2026-05-08T10:00:00",
            "is_owner": True,
        },
    )

    response = authenticated_client.get("/collaboration?channel_id=channel-1")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Collaborative Briefing" in html
    assert "Channels" in html
    assert "Channel Overview" in html
    assert "Partners" in html
    assert "Open Live Room" in html
    assert "Channel Tasks" in html
    assert "Notes" in html
    assert "Recent Activity" in html
    assert ">Close<" not in html
    assert "Impact" not in html
    assert "Key Takeaways" not in html
    assert "Source Labels" not in html
    assert "Briefing Mode" not in html
    assert "Story Focus" not in html
    assert "Story title" not in html
    assert html.count("data-collab-copy-link") == 1
    assert html.index("Second Channel") < html.index("Live Demo")


def test_collaboration_overview_renders_closed_channel_as_read_only_archive(authenticated_client, responses_mock):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/collab/channels",
        json={
            "items": [
                {
                    "channel_id": "channel-1",
                    "topic": "Archived Channel",
                    "status": "closed",
                    "owner_base_url": "https://alpha.demo",
                    "story_count": 1,
                    "participant_count": 2,
                    "created_at": "2026-05-08T10:00:00",
                    "updated_at": "2026-05-08T11:00:00",
                    "invite": {
                        "owner_base_url": "https://alpha.demo",
                        "channel_id": "channel-1",
                        "token": "token-1",
                        "join_url": "/collaboration/join?channel_id=channel-1",
                    },
                }
            ],
            "total_count": 1,
        },
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/collab/channels/channel-1",
        json={
            "channel_id": "channel-1",
            "topic": "Archived Channel",
            "status": "closed",
            "owner_base_url": "https://alpha.demo",
            "active_instance_base_url": "https://alpha.demo",
            "invite": {
                "owner_base_url": "https://alpha.demo",
                "channel_id": "channel-1",
                "token": "token-1",
                "join_url": "/collaboration/join?channel_id=channel-1",
            },
            "participants": [{"base_url": "https://alpha.demo", "role": "owner", "joined_at": "2026-05-08T10:00:00"}],
            "presence": [],
            "locks": [],
            "workspace": {
                "focused_story_id": "snapshot-1",
                "active_mode": "briefing",
                "briefing": {
                    "impact": "High",
                    "key_takeaways": [],
                    "risks": [],
                    "key_questions": [],
                    "related_story_ids": [],
                    "source_labels": [],
                },
                "decisions": [{"id": "decision-1", "text": "Archive this channel", "owner": "alice", "status": "done"}],
                "tasks": [{"id": "task-1", "text": "Verify IOC", "owner": "alice", "status": "done"}],
                "comments": [{"id": "comment-1", "author": "alice", "text": "Final archived note"}],
                "chat_messages": [],
                "timeline_events": [],
                "activity_items": [{"id": "activity-1", "text": "closed channel", "actor": "alice"}],
            },
            "stories": [
                {
                    "id": "snapshot-1",
                    "title": "Archived Story",
                    "description": "Final description",
                    "created": "2026-05-08T10:00:00",
                    "source_instance": "https://alpha.demo",
                    "source_story_id": "story-1",
                    "story": {"id": "story-1", "title": "Archived Story", "summary": "Shared summary", "news_items": []},
                }
            ],
            "result_stories": [],
            "created_at": "2026-05-08T10:00:00",
            "updated_at": "2026-05-08T11:00:00",
            "is_owner": True,
        },
    )

    response = authenticated_client.get("/collaboration?channel_id=channel-1")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Archived Channel" in html
    assert "Archived" in html
    assert "This channel is archived. The snapshot below reflects its final state when it was closed." in html
    assert "This channel is archived and read-only." in html
    assert "Open Live Room" not in html
    assert "Open Archive" in html
    assert "Add channel task" not in html
    assert "Add note" not in html
    assert "Add decision" not in html
    assert "Finalize Stories" not in html
    assert ">Close<" not in html


def test_collaboration_workspace_renders_closed_channel_as_read_only_archive_room(authenticated_client, responses_mock):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/collab/channels",
        json={
            "items": [
                {
                    "channel_id": "channel-1",
                    "topic": "Archived Channel",
                    "status": "closed",
                    "owner_base_url": "https://alpha.demo",
                    "story_count": 1,
                    "participant_count": 2,
                    "created_at": "2026-05-08T10:00:00",
                    "updated_at": "2026-05-08T11:00:00",
                    "invite": {
                        "owner_base_url": "https://alpha.demo",
                        "channel_id": "channel-1",
                        "token": "token-1",
                        "join_url": "/collaboration/join?channel_id=channel-1",
                    },
                }
            ],
            "total_count": 1,
        },
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/collab/channels/channel-1",
        json={
            "channel_id": "channel-1",
            "topic": "Archived Channel",
            "status": "closed",
            "owner_base_url": "https://alpha.demo",
            "active_instance_base_url": "https://alpha.demo",
            "invite": {
                "owner_base_url": "https://alpha.demo",
                "channel_id": "channel-1",
                "token": "token-1",
                "join_url": "/collaboration/join?channel_id=channel-1",
            },
            "participants": [{"base_url": "https://alpha.demo", "role": "owner", "joined_at": "2026-05-08T10:00:00"}],
            "presence": [],
            "locks": [],
            "workspace": {
                "focused_story_id": "snapshot-1",
                "active_mode": "story",
                "briefing": {
                    "impact": "High",
                    "key_takeaways": [],
                    "risks": [],
                    "key_questions": [],
                    "related_story_ids": [],
                    "source_labels": [],
                },
                "decisions": [],
                "tasks": [],
                "comments": [],
                "chat_messages": [{"id": "msg-1", "author": "alice", "text": "Archived chat message"}],
                "timeline_events": [],
                "activity_items": [],
            },
            "stories": [
                {
                    "id": "snapshot-1",
                    "title": "Archived Story",
                    "description": "Final description",
                    "created": "2026-05-08T10:00:00",
                    "source_instance": "https://alpha.demo",
                    "source_story_id": "story-1",
                    "story": {"id": "story-1", "title": "Archived Story", "summary": "Shared summary", "news_items": []},
                }
            ],
            "result_stories": [],
            "created_at": "2026-05-08T10:00:00",
            "updated_at": "2026-05-08T11:00:00",
            "is_owner": True,
        },
    )

    response = authenticated_client.get("/collaboration/channel-1")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Archived Story Room" in html
    assert "Read-only archive of the channel" in html
    assert "Team Chat" in html
    assert "Archived" in html
    assert "Type a message" not in html
    assert "Add channel task" not in html
    assert "Add note" not in html
    assert "Add From Assess" not in html
    assert ">Close<" not in html
    assert "Overview" in html


def test_collaboration_overview_defaults_to_first_archived_channel_when_no_open_channels(authenticated_client, responses_mock):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/collab/channels",
        json={
            "items": [
                {
                    "channel_id": "channel-2",
                    "topic": "Newest Archived",
                    "status": "closed",
                    "owner_base_url": "https://bravo.demo",
                    "story_count": 1,
                    "participant_count": 1,
                    "created_at": "2026-05-08T11:00:00",
                    "updated_at": "2026-05-08T12:00:00",
                    "invite": {
                        "owner_base_url": "https://bravo.demo",
                        "channel_id": "channel-2",
                        "token": "token-2",
                        "join_url": "/collaboration/join?channel_id=channel-2",
                    },
                },
                {
                    "channel_id": "channel-1",
                    "topic": "Older Archived",
                    "status": "closed",
                    "owner_base_url": "https://alpha.demo",
                    "story_count": 1,
                    "participant_count": 2,
                    "created_at": "2026-05-08T10:00:00",
                    "updated_at": "2026-05-08T11:00:00",
                    "invite": {
                        "owner_base_url": "https://alpha.demo",
                        "channel_id": "channel-1",
                        "token": "token-1",
                        "join_url": "/collaboration/join?channel_id=channel-1",
                    },
                },
            ],
            "total_count": 2,
        },
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/collab/channels/channel-2",
        json={
            "channel_id": "channel-2",
            "topic": "Newest Archived",
            "status": "closed",
            "owner_base_url": "https://bravo.demo",
            "active_instance_base_url": "https://bravo.demo",
            "invite": {
                "owner_base_url": "https://bravo.demo",
                "channel_id": "channel-2",
                "token": "token-2",
                "join_url": "/collaboration/join?channel_id=channel-2",
            },
            "participants": [{"base_url": "https://bravo.demo", "role": "owner", "joined_at": "2026-05-08T11:00:00"}],
            "presence": [],
            "locks": [],
            "workspace": {
                "focused_story_id": "snapshot-2",
                "active_mode": "briefing",
                "briefing": {
                    "impact": None,
                    "key_takeaways": [],
                    "risks": [],
                    "key_questions": [],
                    "related_story_ids": [],
                    "source_labels": [],
                },
                "decisions": [],
                "tasks": [],
                "comments": [],
                "chat_messages": [],
                "timeline_events": [],
                "activity_items": [],
            },
            "stories": [
                {
                    "id": "snapshot-2",
                    "title": "Newest Archived Story",
                    "description": "Final state",
                    "created": "2026-05-08T11:00:00",
                    "source_instance": "https://bravo.demo",
                    "source_story_id": "story-2",
                    "story": {"id": "story-2", "title": "Newest Archived Story", "summary": "Summary", "news_items": []},
                }
            ],
            "result_stories": [],
            "created_at": "2026-05-08T11:00:00",
            "updated_at": "2026-05-08T12:00:00",
            "is_owner": True,
        },
    )

    response = authenticated_client.get("/collaboration")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "No Active Collaboration Selected" not in html
    assert "Newest Archived" in html
    assert "Older Archived" in html
    assert "This channel is archived. The snapshot below reflects its final state when it was closed." in html
    assert "Open Live Room" not in html
    assert "Open Archive" in html

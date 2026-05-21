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
    assert "Live Demo" in html
    assert "Story in Channel" in html
    assert "https://bravo.demo" in html
    assert "data-collab-connection-status" in html
    assert "Live sync idle." in html

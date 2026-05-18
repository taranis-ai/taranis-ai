from core.service.collaboration import collaboration_service


def test_create_collaboration_channel_from_story(client, auth_header, stories):
    collaboration_service.channels.clear()

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
    assert len(payload["stories"]) == 1
    assert payload["stories"][0]["source_story_id"] == stories[0]


def test_collaboration_channel_invite_can_be_redeemed_multiple_times(client, auth_header, stories):
    collaboration_service.channels.clear()
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


def test_finalize_collaboration_channel_creates_local_stories(client, auth_header, stories):
    collaboration_service.channels.clear()
    create_response = client.post(
        "/api/assess/collab/channels",
        json={"topic": "Finalize Topic", "story_ids": [stories[0]]},
        headers=auth_header,
    )
    channel_id = create_response.get_json()["channel_id"]

    finalize_response = client.post(f"/api/assess/collab/channels/{channel_id}/finalize", json={}, headers=auth_header)

    assert finalize_response.status_code == 200
    payload = finalize_response.get_json()
    assert payload["channel_id"] == channel_id
    assert payload["created_story_ids"]
    created_story_id = payload["created_story_ids"][0]

    story_response = client.get(f"/api/assess/story/{created_story_id}", headers=auth_header)
    assert story_response.status_code == 200

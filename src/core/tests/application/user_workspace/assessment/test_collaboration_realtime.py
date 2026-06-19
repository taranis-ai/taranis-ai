import asyncio
import json

from starlette.websockets import WebSocketDisconnect

from core.collaboration_realtime import CollaborationRealtimeHub


class PeerSocketStub:
    def __init__(self, messages: list[dict]):
        self._messages = [json.dumps(message) for message in messages]
        self.accepted = False
        self.closed = None
        self.sent_texts: list[str] = []

    async def accept(self):
        self.accepted = True

    async def receive_text(self) -> str:
        if self._messages:
            return self._messages.pop(0)
        raise WebSocketDisconnect()

    async def send_text(self, payload: str):
        self.sent_texts.append(payload)

    async def send(self, _message):
        raise AssertionError("peer websocket bootstrap must use send_text on Starlette WebSocket")

    async def close(self, code: int | None = None, reason: str | None = None):
        self.closed = {"code": code, "reason": reason}


def test_peer_socket_sends_initial_snapshot_via_send_text():
    channel_id = "channel-1"
    token = "invite-token"
    partner_base_url = "https://bravo.demo"
    channel = {
        "channel_id": channel_id,
        "invite": {"token": token},
        "participants": [{"base_url": partner_base_url}],
    }
    websocket = PeerSocketStub(
        [
            {
                "type": "peer.connect",
                "channel_id": channel_id,
                "payload": {"token": token, "partner_base_url": partner_base_url},
            }
        ]
    )
    hub = CollaborationRealtimeHub()

    async def fake_channel_state(requested_channel_id: str):
        assert requested_channel_id == channel_id
        return channel

    hub._channel_state = fake_channel_state

    asyncio.run(hub.peer_socket(websocket))

    assert websocket.accepted is True
    assert websocket.closed is None
    assert len(websocket.sent_texts) == 1
    snapshot_message = json.loads(websocket.sent_texts[0])
    assert snapshot_message["type"] == "collab.state.snapshot"
    assert snapshot_message["payload"]["channel"]["channel_id"] == channel_id


def test_peer_socket_processes_followup_messages_without_async_iteration():
    channel_id = "channel-2"
    token = "invite-token"
    partner_base_url = "https://bravo.demo"
    channel = {
        "channel_id": channel_id,
        "invite": {"token": token},
        "participants": [{"base_url": partner_base_url}],
    }
    websocket = PeerSocketStub(
        [
            {
                "type": "peer.connect",
                "channel_id": channel_id,
                "payload": {"token": token, "partner_base_url": partner_base_url},
            },
            {
                "type": "collab.story.ops.submit",
                "channel_id": channel_id,
                "payload": {
                    "actor": {"username": "alice"},
                    "snapshot_id": "snapshot-1",
                    "field_name": "summary",
                    "version": 0,
                    "op_id": "op-1",
                    "updates": [{"from": 0, "to": 0, "insert": "updated"}],
                },
            },
        ]
    )
    hub = CollaborationRealtimeHub()
    applied_messages: list[dict] = []
    broadcasted_channels: list[dict] = []

    async def fake_channel_state(requested_channel_id: str):
        assert requested_channel_id == channel_id
        return channel

    async def fake_apply_owner_message(requested_channel_id: str, actor: dict, message: dict):
        assert requested_channel_id == channel_id
        applied_messages.append({"actor": actor, "message": message})
        return {"channel": {**channel, "updated": True}, "applied": {"snapshot_id": "snapshot-1", "field_name": "summary"}}

    async def fake_broadcast_event(broadcast_channel_id: str, message_type: str, payload: dict):
        broadcasted_channels.append({"channel_id": broadcast_channel_id, "type": message_type, "payload": payload})

    hub._channel_state = fake_channel_state
    hub._apply_owner_message = fake_apply_owner_message
    hub._broadcast_event = fake_broadcast_event

    asyncio.run(hub.peer_socket(websocket))

    assert len(applied_messages) == 1
    assert applied_messages[0]["actor"]["base_url"] == partner_base_url
    assert applied_messages[0]["message"]["type"] == "collab.story.ops.submit"
    assert len(broadcasted_channels) == 1
    assert broadcasted_channels[0]["type"] == "collab.story.ops.applied"
    assert broadcasted_channels[0]["payload"]["channel"]["updated"] is True


def test_apply_owner_message_supports_workspace_patch():
    hub = CollaborationRealtimeHub()
    recorded = {}

    async def fake_core_post(endpoint: str, payload: dict):
        recorded["endpoint"] = endpoint
        recorded["payload"] = payload
        return {"channel_id": "channel-3", "workspace": {"active_mode": "briefing"}}

    hub._core_post = fake_core_post

    updated = asyncio.run(
        hub._apply_owner_message(
            "channel-3",
            {"base_url": "https://alpha.demo", "session_id": "session-a", "username": "alice"},
            {
                "type": "collab.workspace.patch",
                "payload": {
                    "target": "workspace",
                    "action": "set",
                    "data": {"active_mode": "briefing"},
                },
            },
        )
    )

    assert recorded["endpoint"].endswith("/assess/collab/channels/channel-3/live/workspace-patch")
    assert recorded["payload"]["target"] == "workspace"
    assert updated["workspace"]["active_mode"] == "briefing"


def test_apply_owner_message_supports_story_ops_submit():
    hub = CollaborationRealtimeHub()
    recorded = {}

    async def fake_core_post(endpoint: str, payload: dict):
        recorded["endpoint"] = endpoint
        recorded["payload"] = payload
        return {"channel": {"channel_id": "channel-4"}, "applied": {"field_name": "summary", "version": 1}}

    hub._core_post = fake_core_post

    updated = asyncio.run(
        hub._apply_owner_message(
            "channel-4",
            {"base_url": "https://alpha.demo", "session_id": "session-a", "username": "alice"},
            {
                "type": "collab.story.ops.submit",
                "payload": {
                    "snapshot_id": "snapshot-1",
                    "field_name": "summary",
                    "version": 0,
                    "op_id": "op-1",
                    "updates": [{"from": 0, "to": 0, "insert": "Hi"}],
                },
            },
        )
    )

    assert recorded["endpoint"].endswith("/assess/collab/channels/channel-4/live/story-ops")
    assert recorded["payload"]["field_name"] == "summary"
    assert updated["applied"]["version"] == 1

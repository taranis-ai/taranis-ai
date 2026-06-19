import asyncio
import contextlib
import json
import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx
import websockets
from granian.cli import cli
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from core.config import Config
from core.log import logger


EDITABLE_FIELDS = {"title", "description", "summary", "comments"}


@dataclass
class BrowserSession:
    websocket: WebSocket
    channel_id: str
    session_id: str
    username: str
    selected_story_id: str | None = None


class CollaborationRealtimeHub:
    def __init__(self) -> None:
        self.browser_sessions: dict[str, dict[str, BrowserSession]] = defaultdict(dict)
        self.owner_peer_connections: dict[str, dict[str, WebSocket]] = defaultdict(dict)
        self.participant_owner_tasks: dict[str, asyncio.Task] = {}
        self.participant_owner_sockets: dict[str, Any] = {}
        self.channel_mutexes: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.http_timeout = Config.COLLAB_REALTIME_REQUEST_TIMEOUT
        self.owner_message_handlers = {
            "collab.hello": self._handle_presence_connect,
            "collab.presence": self._handle_presence_connect,
            "collab.presence.disconnect": self._handle_presence_disconnect,
            "collab.lock.acquire": self._handle_lock_acquire,
            "collab.lock.heartbeat": self._handle_lock_heartbeat,
            "collab.lock.release": self._handle_lock_release,
            "collab.story.patch": self._handle_story_patch,
            "collab.story.ops.submit": self._handle_story_ops_submit,
            "collab.story.selection.update": self._handle_selection_update,
            "collab.story.selection.clear": self._handle_selection_clear,
            "collab.news_item.move": self._handle_news_item_move,
            "collab.workspace.patch": self._handle_workspace_patch,
        }
        self.owner_result_broadcasters = {
            "collab.story.ops.submit": self._broadcast_story_ops_applied,
            "collab.story.selection.update": self._broadcast_selection_updated,
            "collab.story.selection.clear": self._broadcast_selection_cleared,
        }

    @staticmethod
    def _message(message_type: str, channel_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"type": message_type, "channel_id": channel_id, "payload": payload or {}}

    @staticmethod
    def _coerce_channel_payload(channel: Any) -> dict[str, Any]:
        if isinstance(channel, dict):
            return channel
        if isinstance(channel, str):
            parsed = json.loads(channel)
            if isinstance(parsed, dict):
                return parsed
        raise TypeError(f"Invalid collaboration channel payload type: {type(channel).__name__}")

    @staticmethod
    def _root_prefix() -> str:
        root = Config.APPLICATION_ROOT.strip("/")
        return f"/{root}" if root else ""

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        parts = urlsplit(base_url.strip())
        path = parts.path.rstrip("/")
        return f"{parts.scheme}://{parts.netloc}{path}"

    def _local_base_url(self) -> str:
        if not Config.COLLAB_EXTERNAL_BASE_URL:
            raise RuntimeError("COLLAB_EXTERNAL_BASE_URL must be configured for collaboration realtime")
        return self._normalize_base_url(Config.COLLAB_EXTERNAL_BASE_URL)

    def _peer_ws_url(self, base_url: str) -> str:
        normalized = self._normalize_base_url(base_url)
        scheme = "wss" if normalized.startswith("https://") else "ws"
        return f"{scheme}://{normalized.split('://', 1)[1]}{self._root_prefix()}/collaboration/ws/peer"

    def _local_core_headers(self, *, cookie: str | None = None) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {Config.API_KEY.get_secret_value()}"}
        if cookie:
            headers["Cookie"] = cookie
        return headers

    async def _core_get(self, endpoint: str, *, cookie: str | None = None, use_api_key: bool = True) -> dict[str, Any]:
        headers = self._local_core_headers(cookie=cookie if not use_api_key else None) if use_api_key else {"Cookie": cookie or ""}
        async with httpx.AsyncClient(timeout=self.http_timeout) as client:
            response = await client.get(f"{Config.COLLAB_CORE_API_URL}{endpoint}", headers=headers)
            response.raise_for_status()
            return response.json()

    async def _core_post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.http_timeout) as client:
            response = await client.post(
                f"{Config.COLLAB_CORE_API_URL}{endpoint}",
                headers=self._local_core_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def _authenticate_browser(self, websocket: WebSocket) -> dict[str, Any]:
        cookie_header = websocket.headers.get("cookie", "")
        if not cookie_header:
            raise PermissionError("Missing session cookies")
        try:
            return await self._core_get("/users/", cookie=cookie_header, use_api_key=False)
        except httpx.HTTPError as exc:
            raise PermissionError("Unauthorized collaboration session") from exc

    async def _channel_state(self, channel_id: str) -> dict[str, Any]:
        return await self._core_get(f"/assess/collab/channels/{channel_id}/live-state")

    async def _sync_local_channel(self, channel: dict[str, Any]) -> dict[str, Any]:
        invite = channel.get("invite") or {}
        return await self._core_post(
            f"/assess/collab/channels/{channel['channel_id']}/remote-sync",
            {"token": invite.get("token", ""), "channel": channel},
        )

    async def _broadcast_to_browsers(self, channel_id: str, message: dict[str, Any]) -> None:
        stale_sessions: list[str] = []
        for session_id, session in self.browser_sessions.get(channel_id, {}).items():
            try:
                await session.websocket.send_json(message)
            except Exception:
                stale_sessions.append(session_id)
        for session_id in stale_sessions:
            self.browser_sessions[channel_id].pop(session_id, None)

    async def _broadcast_to_owner_peers(self, channel_id: str, message: dict[str, Any]) -> None:
        stale_peers: list[str] = []
        for peer_base_url, websocket in self.owner_peer_connections.get(channel_id, {}).items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception:
                stale_peers.append(peer_base_url)
        for peer_base_url in stale_peers:
            self.owner_peer_connections[channel_id].pop(peer_base_url, None)

    async def _broadcast_state(self, channel: dict[str, Any], *, snapshot: bool = False, session_id: str | None = None) -> None:
        channel = self._coerce_channel_payload(channel)
        channel_id = channel["channel_id"]
        message_type = "collab.state.snapshot" if snapshot else "collab.state.updated"
        payload = {"channel": channel}
        if session_id:
            payload["session_id"] = session_id
        message = self._message(message_type, channel_id, payload)
        await self._broadcast_to_browsers(channel_id, message)
        await self._broadcast_to_owner_peers(channel_id, message)

    async def _broadcast_event(self, channel_id: str, message_type: str, payload: dict[str, Any]) -> None:
        message = self._message(message_type, channel_id, payload)
        await self._broadcast_to_browsers(channel_id, message)
        await self._broadcast_to_owner_peers(channel_id, message)

    async def _send_error(self, websocket: WebSocket, channel_id: str, message: str, original_type: str = "") -> None:
        await websocket.send_json(self._message("collab.error", channel_id, {"message": message, "original_type": original_type}))

    def _actor_payload(self, session: BrowserSession) -> dict[str, Any]:
        return {
            "base_url": self._local_base_url(),
            "session_id": session.session_id,
            "username": session.username,
        }

    async def _handle_presence_connect(self, channel_id: str, actor: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        return await self._core_post(
            f"/assess/collab/channels/{channel_id}/live/presence/connect",
            {"actor": actor, "selected_story_id": payload.get("selected_story_id")},
        )

    async def _handle_presence_disconnect(self, channel_id: str, actor: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        return await self._core_post(
            f"/assess/collab/channels/{channel_id}/live/presence/disconnect",
            {"actor": actor, "selected_story_id": payload.get("selected_story_id")},
        )

    async def _handle_lock_acquire(self, channel_id: str, actor: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        return await self._core_post(
            f"/assess/collab/channels/{channel_id}/live/lock/acquire",
            {
                "actor": actor,
                "snapshot_id": payload.get("snapshot_id"),
                "field_name": payload.get("field_name"),
                "selected_story_id": payload.get("selected_story_id"),
            },
        )

    async def _handle_lock_heartbeat(self, channel_id: str, actor: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        return await self._core_post(
            f"/assess/collab/channels/{channel_id}/live/lock/heartbeat",
            {
                "actor": actor,
                "snapshot_id": payload.get("snapshot_id"),
                "field_name": payload.get("field_name"),
                "selected_story_id": payload.get("selected_story_id"),
            },
        )

    async def _handle_lock_release(self, channel_id: str, actor: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        return await self._core_post(
            f"/assess/collab/channels/{channel_id}/live/lock/release",
            {
                "actor": actor,
                "snapshot_id": payload.get("snapshot_id"),
                "field_name": payload.get("field_name"),
                "selected_story_id": payload.get("selected_story_id"),
            },
        )

    async def _handle_story_patch(self, channel_id: str, actor: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        fields = payload.get("fields") or {}
        filtered_fields = {key: value for key, value in fields.items() if key in EDITABLE_FIELDS}
        return await self._core_post(
            f"/assess/collab/channels/{channel_id}/live/story-patch",
            {
                "actor": actor,
                "snapshot_id": payload.get("snapshot_id"),
                "payload": filtered_fields,
            },
        )

    async def _handle_story_ops_submit(self, channel_id: str, actor: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        return await self._core_post(
            f"/assess/collab/channels/{channel_id}/live/story-ops",
            {
                "actor": actor,
                "snapshot_id": payload.get("snapshot_id"),
                "field_name": payload.get("field_name"),
                "version": payload.get("version", 0),
                "op_id": payload.get("op_id"),
                "updates": payload.get("updates") or [],
            },
        )

    async def _handle_selection_update(self, channel_id: str, actor: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        return await self._core_post(
            f"/assess/collab/channels/{channel_id}/live/selection/update",
            {
                "actor": actor,
                "snapshot_id": payload.get("snapshot_id"),
                "field_name": payload.get("field_name"),
                "anchor": payload.get("anchor", 0),
                "head": payload.get("head", 0),
            },
        )

    async def _handle_selection_clear(self, channel_id: str, actor: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        return await self._core_post(
            f"/assess/collab/channels/{channel_id}/live/selection/clear",
            {
                "actor": actor,
                "snapshot_id": payload.get("snapshot_id"),
                "field_name": payload.get("field_name"),
            },
        )

    async def _handle_news_item_move(self, channel_id: str, actor: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        return await self._core_post(
            f"/assess/collab/channels/{channel_id}/live/move-news-item",
            {
                "actor": actor,
                "source_snapshot_id": payload.get("source_snapshot_id"),
                "target_snapshot_id": payload.get("target_snapshot_id"),
                "news_item_id": payload.get("news_item_id"),
            },
        )

    async def _handle_workspace_patch(self, channel_id: str, actor: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        return await self._core_post(
            f"/assess/collab/channels/{channel_id}/live/workspace-patch",
            {
                "actor": actor,
                "target": payload.get("target"),
                "action": payload.get("action"),
                "item_id": payload.get("item_id"),
                "data": payload.get("data") or {},
            },
        )

    async def _apply_owner_message(self, channel_id: str, actor: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
        message_type = message.get("type", "")
        payload = message.get("payload", {})
        handler = self.owner_message_handlers.get(message_type)
        if handler is None:
            raise ValueError(f"Unsupported collaboration message type: {message_type}")
        return await handler(channel_id, actor, payload)

    async def _broadcast_story_ops_applied(self, channel_id: str, updated_payload: dict[str, Any]) -> None:
        await self._broadcast_event(
            channel_id,
            "collab.story.ops.applied",
            {
                **(updated_payload.get("applied") or {}),
                "channel": updated_payload.get("channel"),
            },
        )

    async def _broadcast_selection_updated(self, channel_id: str, updated_payload: dict[str, Any]) -> None:
        await self._broadcast_event(
            channel_id,
            "collab.story.selection.update",
            {
                **(updated_payload.get("selection") or {}),
                "channel": updated_payload.get("channel"),
            },
        )

    async def _broadcast_selection_cleared(self, channel_id: str, updated_payload: dict[str, Any]) -> None:
        await self._broadcast_event(
            channel_id,
            "collab.story.selection.clear",
            {
                **(updated_payload.get("cleared") or {}),
                "channel": updated_payload.get("channel"),
            },
        )

    async def _broadcast_owner_result(self, channel_id: str, message_type: str, updated_payload: dict[str, Any]) -> None:
        broadcaster = self.owner_result_broadcasters.get(message_type)
        if broadcaster is not None:
            await broadcaster(channel_id, updated_payload)
            return
        await self._broadcast_state(updated_payload)

    async def _ensure_participant_owner_connection(self, channel: dict[str, Any]) -> None:
        channel_id = channel["channel_id"]
        if channel.get("owner_base_url") == self._local_base_url():
            return
        existing_task = self.participant_owner_tasks.get(channel_id)
        if existing_task and not existing_task.done():
            return
        self.participant_owner_tasks[channel_id] = asyncio.create_task(
            self._participant_owner_loop(channel_id), name=f"collab-owner-{channel_id}"
        )

    async def _participant_owner_loop(self, channel_id: str) -> None:
        while self.browser_sessions.get(channel_id):
            try:
                channel = await self._channel_state(channel_id)
                invite = channel.get("invite") or {}
                ws_url = self._peer_ws_url(channel["owner_base_url"])
                async with websockets.connect(
                    ws_url,
                    max_size=None,
                ) as websocket:
                    self.participant_owner_sockets[channel_id] = websocket
                    await websocket.send(
                        json.dumps(
                            self._message(
                                "peer.connect",
                                channel_id,
                                {
                                    "token": invite.get("token", ""),
                                    "partner_base_url": self._local_base_url(),
                                },
                            )
                        )
                    )
                    async for raw_message in websocket:
                        message = json.loads(raw_message)
                        if message.get("type") not in {
                            "collab.state.snapshot",
                            "collab.state.updated",
                            "collab.story.ops.applied",
                            "collab.story.selection.update",
                            "collab.story.selection.clear",
                        }:
                            continue
                        payload = message.get("payload") or {}
                        authoritative_channel = payload.get("channel")
                        synced_channel = None
                        if authoritative_channel:
                            synced_channel = await self._sync_local_channel(self._coerce_channel_payload(authoritative_channel))
                        if message.get("type") in {"collab.state.snapshot", "collab.state.updated"}:
                            await self._broadcast_to_browsers(
                                channel_id,
                                self._message(message["type"], channel_id, {"channel": synced_channel}),
                            )
                            continue
                        browser_payload = {key: value for key, value in payload.items() if key != "channel"}
                        if synced_channel is not None:
                            browser_payload["channel"] = synced_channel
                        await self._broadcast_to_browsers(channel_id, self._message(message["type"], channel_id, browser_payload))
            except Exception as exc:
                logger.warning(f"Collaboration peer loop for {channel_id} disconnected: {exc}")
                await asyncio.sleep(1)
            finally:
                self.participant_owner_sockets.pop(channel_id, None)
        self.participant_owner_tasks.pop(channel_id, None)

    async def _forward_to_owner(self, channel_id: str, message: dict[str, Any], actor: dict[str, Any]) -> None:
        channel = await self._channel_state(channel_id)
        await self._ensure_participant_owner_connection(channel)
        websocket = self.participant_owner_sockets.get(channel_id)
        for _ in range(20):
            if websocket is not None:
                break
            await asyncio.sleep(0.1)
            websocket = self.participant_owner_sockets.get(channel_id)
        if websocket is None:
            raise RuntimeError("Owner websocket is not connected")
        payload = dict(message.get("payload") or {})
        payload["actor"] = actor
        await websocket.send(json.dumps(self._message(message.get("type", ""), channel_id, payload)))

    async def browser_socket(self, websocket: WebSocket) -> None:
        channel_id = websocket.query_params.get("channel_id", "").strip()
        if not channel_id:
            await websocket.close(code=4400, reason="Missing channel_id")
            return
        try:
            user = await self._authenticate_browser(websocket)
            channel = await self._channel_state(channel_id)
        except PermissionError:
            await websocket.close(code=4401, reason="Unauthorized")
            return
        except Exception as exc:
            logger.warning(f"Failed to initialize collaboration browser socket: {exc}")
            await websocket.close(code=1011, reason="Failed to initialize collaboration")
            return

        await websocket.accept()
        session = BrowserSession(
            websocket=websocket,
            channel_id=channel_id,
            session_id=str(uuid.uuid4()),
            username=user.get("username") or user.get("name") or "unknown",
            selected_story_id=websocket.query_params.get("story_id"),
        )
        self.browser_sessions[channel_id][session.session_id] = session
        actor = self._actor_payload(session)
        current_message_type = "collab.hello"

        try:
            if channel.get("owner_base_url") == self._local_base_url():
                channel = await self._apply_owner_message(
                    channel_id,
                    actor,
                    self._message("collab.hello", channel_id, {"selected_story_id": session.selected_story_id}),
                )
            else:
                await self._forward_to_owner(
                    channel_id,
                    self._message("collab.hello", channel_id, {"selected_story_id": session.selected_story_id}),
                    actor,
                )
            await websocket.send_json(
                self._message("collab.state.snapshot", channel_id, {"channel": channel, "session_id": session.session_id})
            )

            while True:
                message = await websocket.receive_json()
                current_message_type = message.get("type", "")
                session.selected_story_id = (message.get("payload") or {}).get("selected_story_id") or session.selected_story_id
                actor = self._actor_payload(session)
                if channel.get("owner_base_url") == self._local_base_url():
                    async with self.channel_mutexes[channel_id]:
                        updated_payload = await self._apply_owner_message(channel_id, actor, message)
                    await self._broadcast_owner_result(channel_id, current_message_type, updated_payload)
                else:
                    await self._forward_to_owner(channel_id, message, actor)
        except WebSocketDisconnect:
            pass
        except httpx.HTTPStatusError as exc:
            response_message = exc.response.text
            await self._send_error(websocket, channel_id, response_message or "Collaboration update failed", current_message_type)
        except Exception as exc:
            logger.warning(f"Collaboration browser socket error for {channel_id}: {exc}")
            with contextlib.suppress(Exception):
                await self._send_error(websocket, channel_id, str(exc), "")
        finally:
            self.browser_sessions[channel_id].pop(session.session_id, None)
            with contextlib.suppress(Exception):
                disconnect_message = self._message(
                    "collab.presence.disconnect",
                    channel_id,
                    {"selected_story_id": session.selected_story_id},
                )
                if channel.get("owner_base_url") == self._local_base_url():
                    async with self.channel_mutexes[channel_id]:
                        updated_channel = await self._apply_owner_message(channel_id, actor, disconnect_message)
                    await self._broadcast_state(updated_channel)
                else:
                    await self._forward_to_owner(channel_id, disconnect_message, actor)
            if not self.browser_sessions.get(channel_id):
                task = self.participant_owner_tasks.get(channel_id)
                if task:
                    task.cancel()
                    with contextlib.suppress(Exception):
                        await task

    async def peer_socket(self, websocket: WebSocket) -> None:
        await websocket.accept()

        channel_id = ""
        partner_base_url = ""
        try:
            raw_message = await websocket.receive_text()
            message = json.loads(raw_message)
            if message.get("type") != "peer.connect":
                await websocket.close(code=4400, reason="Missing peer.connect")
                return
            channel_id = message.get("channel_id", "")
            payload = message.get("payload") or {}
            partner_base_url = self._normalize_base_url(payload.get("partner_base_url", ""))
            channel = await self._channel_state(channel_id)
            participants = {item.get("base_url") for item in channel.get("participants", [])}
            if payload.get("token") != ((channel.get("invite") or {}).get("token", "")) or partner_base_url not in participants:
                await websocket.close(code=4403, reason="Invalid collaboration peer")
                return

            self.owner_peer_connections[channel_id][partner_base_url] = websocket
            await websocket.send_text(json.dumps(self._message("collab.state.snapshot", channel_id, {"channel": channel})))

            while True:
                raw_message = await websocket.receive_text()
                message = json.loads(raw_message)
                payload = dict(message.get("payload") or {})
                actor = dict(payload.get("actor") or {})
                actor["base_url"] = partner_base_url
                async with self.channel_mutexes[channel_id]:
                    updated_payload = await self._apply_owner_message(
                        channel_id, actor, self._message(message.get("type", ""), channel_id, payload)
                    )
                await self._broadcast_owner_result(channel_id, message.get("type", ""), updated_payload)
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            logger.exception(f"Collaboration peer socket error for {channel_id}: {exc}")
        finally:
            if channel_id and partner_base_url:
                self.owner_peer_connections[channel_id].pop(partner_base_url, None)


hub = CollaborationRealtimeHub()


async def healthcheck(_request):
    return PlainTextResponse("ok")


app = Starlette(
    routes=[
        Route("/healthz", healthcheck),
        WebSocketRoute("/collaboration/ws", hub.browser_socket),
        WebSocketRoute("/collaboration/ws/peer", hub.peer_socket),
    ]
)


def main():
    cli(
        [
            "--interface",
            "asgi",
            "--host",
            Config.COLLAB_REALTIME_HOST,
            "--port",
            str(Config.COLLAB_REALTIME_PORT),
            "core.collaboration_realtime:app",
        ]
    )

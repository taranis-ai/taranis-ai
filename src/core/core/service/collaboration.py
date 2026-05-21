import copy
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote, urlsplit

import requests
from flask import has_request_context, request
from itsdangerous import BadSignature, URLSafeSerializer
from models.collaboration import (
    CollabChannelDetail,
    CollabChannelSummary,
    CollabFieldLock,
    CollabFinalizeResult,
    CollabInvite,
    CollabParticipant,
    CollabPresence,
    CollabStorySnapshot,
)

from core.config import Config
from core.log import logger
from core.managers.sse_manager import sse_manager
from core.model.story import Story
from core.model.user import User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CollaborationService:
    def __init__(self):
        self.channels: dict[str, dict[str, Any]] = {}
        self.serializer = URLSafeSerializer(Config.API_KEY.get_secret_value(), salt="collaboration-channel")
        self.timeout = 15
        self.lock_ttl_seconds = 10

    def _sync_channel_to_participant(self, channel_id: str, base_url: str, sync_payload: dict[str, Any]) -> None:
        try:
            requests.post(
                f"{self.api_root_url(base_url)}/assess/collab/channels/{channel_id}/remote-sync",
                json=sync_payload,
                headers={"Content-type": "application/json"},
                timeout=self.timeout,
            )
        except requests.RequestException:
            logger.warning(f"Failed to sync collaboration channel {channel_id} to {base_url}")

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        parts = urlsplit(base_url.strip())
        path = parts.path.rstrip("/")
        return f"{parts.scheme}://{parts.netloc}{path}"

    @classmethod
    def external_base_url(cls) -> str:
        if Config.COLLAB_EXTERNAL_BASE_URL:
            return cls._normalize_base_url(Config.COLLAB_EXTERNAL_BASE_URL)
        if has_request_context():
            forwarded_base_url = request.headers.get("X-Taranis-External-Base-Url", "").strip()
            if forwarded_base_url:
                return cls._normalize_base_url(forwarded_base_url)
            forwarded_proto = request.headers.get("X-Forwarded-Proto", "").strip()
            scheme = forwarded_proto or request.scheme or "http"
            host = request.headers.get("X-Forwarded-Host", "").strip() or request.host
            if host:
                return cls._normalize_base_url(f"{scheme}://{host}")
        raise RuntimeError("COLLAB_EXTERNAL_BASE_URL is not configured and no active request is available to derive it.")

    @classmethod
    def frontend_root_url(cls, base_url: str | None = None) -> str:
        base = cls._normalize_base_url(base_url or cls.external_base_url())
        root = Config.APPLICATION_ROOT.strip("/")
        prefix = f"/{root}" if root else ""
        return f"{base}{prefix}/frontend"

    @classmethod
    def frontend_root_path(cls) -> str:
        root = Config.APPLICATION_ROOT.strip("/")
        prefix = f"/{root}" if root else ""
        return f"{prefix}/frontend"

    @classmethod
    def api_root_url(cls, base_url: str | None = None) -> str:
        base = cls._normalize_base_url(base_url or cls.external_base_url())
        root = Config.APPLICATION_ROOT.strip("/")
        prefix = f"/{root}" if root else ""
        return f"{base}{prefix}/api"

    def _build_invite(self, channel_id: str, token: str, owner_base_url: str) -> CollabInvite:
        query = f"owner_base_url={quote(owner_base_url, safe='')}&channel_id={quote(channel_id, safe='')}&token={quote(token, safe='')}"
        join_url = f"{self.frontend_root_path()}/collaboration/join?{query}"
        return CollabInvite(owner_base_url=owner_base_url, channel_id=channel_id, token=token, join_url=join_url)

    def _build_token(self, channel_id: str) -> str:
        return self.serializer.dumps({"channel_id": channel_id, "owner_base_url": self.external_base_url()})

    def _validate_token(self, channel_id: str, token: str) -> bool:
        try:
            payload = self.serializer.loads(token)
        except BadSignature:
            return False
        return payload.get("channel_id") == channel_id and payload.get("owner_base_url") == self.external_base_url()

    @staticmethod
    def _build_snapshot_from_story(story_payload: dict[str, Any], source_instance: str) -> CollabStorySnapshot:
        return CollabStorySnapshot(
            id=str(uuid.uuid4()),
            title=story_payload.get("title"),
            description=story_payload.get("description"),
            created=story_payload.get("created"),
            source_instance=source_instance,
            source_story_id=story_payload.get("id"),
            story=copy.deepcopy(story_payload),
        )

    @staticmethod
    def _snapshot_key(snapshot: CollabStorySnapshot) -> tuple[str | None, str | None]:
        return snapshot.source_instance, snapshot.source_story_id

    def _merge_story_snapshots(self, channel_state: dict[str, Any], snapshots: list[CollabStorySnapshot]) -> bool:
        changed = False
        existing = {
            self._snapshot_key(CollabStorySnapshot.model_validate(snapshot)): index for index, snapshot in enumerate(channel_state["stories"])
        }
        for snapshot in snapshots:
            key = self._snapshot_key(snapshot)
            if key in existing:
                channel_state["stories"][existing[key]] = snapshot.model_dump(mode="json")
            else:
                channel_state["stories"].append(snapshot.model_dump(mode="json"))
            changed = True
        if changed:
            channel_state["result_stories"] = copy.deepcopy(channel_state["stories"])
            self._touch_channel(channel_state)
        return changed

    @staticmethod
    def _story_fields_snapshot(story_payload: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
        snapshot["title"] = story_payload.get("title")
        snapshot["description"] = story_payload.get("description")
        return snapshot

    def _replace_story_snapshot(self, channel_state: dict[str, Any], snapshot_id: str, story_payload: dict[str, Any]) -> bool:
        changed = False
        for key in ("stories", "result_stories"):
            for snapshot in channel_state[key]:
                if snapshot.get("id") == snapshot_id:
                    snapshot["story"] = copy.deepcopy(story_payload)
                    self._story_fields_snapshot(story_payload, snapshot)
                    changed = True
        if changed:
            self._touch_channel(channel_state)
        return changed

    @staticmethod
    def _find_snapshot(channel_state: dict[str, Any], snapshot_id: str) -> dict[str, Any] | None:
        for snapshot in channel_state["stories"]:
            if snapshot.get("id") == snapshot_id:
                return snapshot
        return None

    @staticmethod
    def _lock_key(snapshot_id: str, field_name: str) -> str:
        return f"{snapshot_id}:{field_name}"

    @staticmethod
    def _touch_channel(channel_state: dict[str, Any]) -> None:
        channel_state["updated_at"] = _utcnow().isoformat()

    def _prune_runtime_state(self, channel_state: dict[str, Any]) -> None:
        now = _utcnow()
        valid_locks = []
        for lock in channel_state.get("locks", []):
            expires_at = lock.get("expires_at")
            if not expires_at:
                continue
            try:
                if datetime.fromisoformat(expires_at) <= now:
                    continue
            except ValueError:
                continue
            valid_locks.append(lock)
        channel_state["locks"] = valid_locks

    def _upsert_presence(
        self,
        channel_state: dict[str, Any],
        *,
        session_id: str,
        participant_base_url: str,
        username: str,
        selected_story_id: str | None = None,
    ) -> None:
        now = _utcnow().isoformat()
        for presence in channel_state.get("presence", []):
            if presence.get("session_id") == session_id:
                presence["participant_base_url"] = participant_base_url
                presence["username"] = username
                presence["selected_story_id"] = selected_story_id
                presence["last_seen_at"] = now
                return
        channel_state.setdefault("presence", []).append(
            {
                "session_id": session_id,
                "participant_base_url": participant_base_url,
                "username": username,
                "connected_at": now,
                "last_seen_at": now,
                "selected_story_id": selected_story_id,
            }
        )

    def _remove_presence(self, channel_state: dict[str, Any], session_id: str) -> bool:
        existing = channel_state.get("presence", [])
        remaining = [presence for presence in existing if presence.get("session_id") != session_id]
        if len(remaining) == len(existing):
            return False
        channel_state["presence"] = remaining
        channel_state["locks"] = [lock for lock in channel_state.get("locks", []) if lock.get("session_id") != session_id]
        self._touch_channel(channel_state)
        return True

    def _channel_to_detail(self, channel_state: dict[str, Any], active_instance_base_url: str | None = None) -> CollabChannelDetail:
        self._prune_runtime_state(channel_state)
        invite = self._build_invite(channel_state["channel_id"], channel_state["token"], channel_state["owner_base_url"])
        participants = [CollabParticipant.model_validate(item) for item in channel_state["participants"]]
        presence = [CollabPresence.model_validate(item) for item in channel_state.get("presence", [])]
        locks = [CollabFieldLock.model_validate(item) for item in channel_state.get("locks", [])]
        stories = [CollabStorySnapshot.model_validate(item) for item in channel_state["stories"]]
        result_stories = [CollabStorySnapshot.model_validate(item) for item in channel_state["result_stories"]]
        active_base_url = active_instance_base_url or self.external_base_url()
        return CollabChannelDetail(
            channel_id=channel_state["channel_id"],
            topic=channel_state["topic"],
            status=channel_state["status"],
            owner_base_url=channel_state["owner_base_url"],
            active_instance_base_url=active_base_url,
            invite=invite,
            participants=participants,
            presence=presence,
            locks=locks,
            stories=stories,
            result_stories=result_stories,
            created_at=channel_state["created_at"],
            updated_at=channel_state["updated_at"],
            is_owner=channel_state["owner_base_url"] == active_base_url,
        )

    def _channel_to_summary(self, channel_state: dict[str, Any]) -> CollabChannelSummary:
        invite = self._build_invite(channel_state["channel_id"], channel_state["token"], channel_state["owner_base_url"])
        return CollabChannelSummary(
            channel_id=channel_state["channel_id"],
            topic=channel_state["topic"],
            status=channel_state["status"],
            owner_base_url=channel_state["owner_base_url"],
            story_count=len(channel_state["stories"]),
            participant_count=len(channel_state["participants"]),
            created_at=channel_state["created_at"],
            updated_at=channel_state["updated_at"],
            invite=invite,
        )

    def _broadcast_update(
        self,
        channel_state: dict[str, Any],
        closed: bool = False,
        skip_participants: set[str] | None = None,
    ) -> None:
        detail = self._channel_to_detail(channel_state)
        payload = detail.model_dump(mode="json")
        if closed:
            sse_manager.collab_channel_closed(payload)
        else:
            sse_manager.collab_channel_updated(payload)

        skipped = {self._normalize_base_url(base_url) for base_url in (skip_participants or set()) if base_url}
        sync_payload = {"token": channel_state["token"], "channel": payload}
        for participant in channel_state["participants"]:
            base_url = participant["base_url"]
            if base_url == channel_state["owner_base_url"] or base_url in skipped:
                continue
            threading.Thread(
                target=self._sync_channel_to_participant,
                args=(channel_state["channel_id"], base_url, sync_payload),
                daemon=True,
            ).start()

    def _require_channel(self, channel_id: str) -> dict[str, Any]:
        channel = self.channels.get(channel_id)
        if channel is None:
            raise KeyError(channel_id)
        return channel

    def list_channels(self) -> dict[str, Any]:
        items = [self._channel_to_summary(channel).model_dump(mode="json") for channel in self.channels.values()]
        items.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
        return {"items": items, "total_count": len(items)}

    def get_channel(self, channel_id: str, active_instance_base_url: str | None = None) -> CollabChannelDetail:
        return self._channel_to_detail(self._require_channel(channel_id), active_instance_base_url=active_instance_base_url)

    def create_channel(self, topic: str, story_payloads: list[dict[str, Any]]) -> CollabChannelDetail:
        channel_id = str(uuid.uuid4())
        token = self._build_token(channel_id)
        now = _utcnow()
        channel_state = {
            "channel_id": channel_id,
            "topic": topic.strip(),
            "status": "open",
            "token": token,
            "owner_base_url": self.external_base_url(),
            "participants": [
                {
                    "base_url": self.external_base_url(),
                    "role": "owner",
                    "joined_at": now.isoformat(),
                }
            ],
            "presence": [],
            "locks": [],
            "stories": [],
            "result_stories": [],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        snapshots = [self._build_snapshot_from_story(payload, self.external_base_url()) for payload in story_payloads]
        self._merge_story_snapshots(channel_state, snapshots)
        self.channels[channel_id] = channel_state
        self._broadcast_update(channel_state)
        return self._channel_to_detail(channel_state)

    def join_owner_channel(self, channel_id: str, token: str, partner_base_url: str) -> CollabChannelDetail:
        channel_state = self._require_channel(channel_id)
        if channel_state["status"] != "open":
            raise ValueError("Channel is closed")
        if not self._validate_token(channel_id, token):
            raise PermissionError("Invalid collaboration token")
        normalized_base_url = self._normalize_base_url(partner_base_url)
        if normalized_base_url not in {participant["base_url"] for participant in channel_state["participants"]}:
            channel_state["participants"].append({"base_url": normalized_base_url, "role": "participant", "joined_at": _utcnow().isoformat()})
            self._touch_channel(channel_state)
            self._broadcast_update(channel_state, skip_participants={normalized_base_url})
        return self._channel_to_detail(channel_state, active_instance_base_url=normalized_base_url)

    def redeem_invite(self, owner_base_url: str, channel_id: str, token: str) -> CollabChannelDetail:
        partner_base_url = self.external_base_url()
        response = requests.post(
            f"{self.api_root_url(owner_base_url)}/assess/collab/channels/{channel_id}/join",
            json={"token": token, "partner_base_url": partner_base_url},
            headers={"Content-type": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        detail = CollabChannelDetail.model_validate(response.json())
        channel_state = detail.model_dump(mode="json")
        channel_state["token"] = token
        channel_state.setdefault("presence", [])
        channel_state.setdefault("locks", [])
        self.channels[channel_id] = channel_state
        sse_manager.collab_channel_updated(detail.model_dump(mode="json"))
        return self._channel_to_detail(channel_state, active_instance_base_url=partner_base_url)

    def apply_remote_sync(self, channel_id: str, token: str, channel_payload: dict[str, Any]) -> CollabChannelDetail:
        if channel_payload.get("channel_id") != channel_id:
            raise ValueError("Channel payload mismatch")
        existing = self.channels.get(channel_id)
        if existing and existing.get("token") != token:
            raise PermissionError("Invalid collaboration token")
        channel_state = copy.deepcopy(channel_payload)
        channel_state["token"] = token
        channel_state.setdefault("presence", [])
        channel_state.setdefault("locks", [])
        self.channels[channel_id] = channel_state
        detail = self._channel_to_detail(channel_state, active_instance_base_url=self.external_base_url())
        if detail.status == "closed":
            sse_manager.collab_channel_closed(detail.model_dump(mode="json"))
        else:
            sse_manager.collab_channel_updated(detail.model_dump(mode="json"))
        return detail

    def _assert_known_participant(self, channel_state: dict[str, Any], partner_base_url: str) -> None:
        normalized = self._normalize_base_url(partner_base_url)
        if normalized not in {participant["base_url"] for participant in channel_state["participants"]}:
            raise PermissionError("Unknown collaboration participant")

    def _apply_story_update(self, channel_state: dict[str, Any], snapshot_id: str, payload: dict[str, Any]) -> None:
        snapshot = self._find_snapshot(channel_state, snapshot_id)
        if snapshot is None:
            raise KeyError(snapshot_id)
        story_payload = copy.deepcopy(snapshot.get("story") or {})
        for field in ("title", "description", "summary", "comments"):
            if field in payload:
                story_payload[field] = payload.get(field) or ""
        self._replace_story_snapshot(channel_state, snapshot_id, story_payload)

    def _apply_move_news_item(
        self,
        channel_state: dict[str, Any],
        source_snapshot_id: str,
        target_snapshot_id: str,
        news_item_id: str,
    ) -> None:
        if source_snapshot_id == target_snapshot_id:
            raise ValueError("Source and target stories must differ")

        source_snapshot = self._find_snapshot(channel_state, source_snapshot_id)
        target_snapshot = self._find_snapshot(channel_state, target_snapshot_id)
        if source_snapshot is None or target_snapshot is None:
            raise KeyError("Collaboration story not found")

        source_story = copy.deepcopy(source_snapshot.get("story") or {})
        target_story = copy.deepcopy(target_snapshot.get("story") or {})
        source_news = list(source_story.get("news_items") or [])
        target_news = list(target_story.get("news_items") or [])

        moved_item = None
        remaining_news: list[dict[str, Any]] = []
        for news_item in source_news:
            if isinstance(news_item, dict) and news_item.get("id") == news_item_id and moved_item is None:
                moved_item = news_item
            else:
                remaining_news.append(news_item)
        if moved_item is None:
            raise KeyError(news_item_id)

        target_news.append(moved_item)
        source_story["news_items"] = remaining_news
        target_story["news_items"] = target_news

        self._replace_story_snapshot(channel_state, source_snapshot_id, source_story)
        self._replace_story_snapshot(channel_state, target_snapshot_id, target_story)

    def _assert_field_lock(
        self,
        channel_state: dict[str, Any],
        snapshot_id: str,
        field_name: str,
        *,
        session_id: str,
    ) -> None:
        self._prune_runtime_state(channel_state)
        lock_key = self._lock_key(snapshot_id, field_name)
        for lock in channel_state.get("locks", []):
            if self._lock_key(lock.get("snapshot_id", ""), lock.get("field_name", "")) != lock_key:
                continue
            if lock.get("session_id") == session_id:
                return
            raise PermissionError(f"Field {field_name} is locked by {lock.get('username', 'another participant')}")

    def register_presence(
        self,
        channel_id: str,
        *,
        participant_base_url: str,
        session_id: str,
        username: str,
        selected_story_id: str | None = None,
    ) -> CollabChannelDetail:
        channel_state = self._require_channel(channel_id)
        self._upsert_presence(
            channel_state,
            session_id=session_id,
            participant_base_url=self._normalize_base_url(participant_base_url),
            username=username,
            selected_story_id=selected_story_id,
        )
        self._touch_channel(channel_state)
        return self._channel_to_detail(channel_state, active_instance_base_url=participant_base_url)

    def unregister_presence(self, channel_id: str, session_id: str, active_instance_base_url: str | None = None) -> CollabChannelDetail:
        channel_state = self._require_channel(channel_id)
        self._remove_presence(channel_state, session_id)
        return self._channel_to_detail(channel_state, active_instance_base_url=active_instance_base_url)

    def acquire_field_lock(
        self,
        channel_id: str,
        *,
        snapshot_id: str,
        field_name: str,
        participant_base_url: str,
        session_id: str,
        username: str,
        selected_story_id: str | None = None,
    ) -> CollabChannelDetail:
        channel_state = self._require_channel(channel_id)
        if channel_state["status"] != "open":
            raise ValueError("Channel is closed")
        self._upsert_presence(
            channel_state,
            session_id=session_id,
            participant_base_url=self._normalize_base_url(participant_base_url),
            username=username,
            selected_story_id=selected_story_id,
        )
        self._assert_field_lock(channel_state, snapshot_id, field_name, session_id=session_id)
        now = _utcnow()
        expires_at = now + timedelta(seconds=self.lock_ttl_seconds)
        channel_state["locks"] = [
            lock
            for lock in channel_state.get("locks", [])
            if self._lock_key(lock.get("snapshot_id", ""), lock.get("field_name", "")) != self._lock_key(snapshot_id, field_name)
        ]
        channel_state["locks"].append(
            {
                "snapshot_id": snapshot_id,
                "field_name": field_name,
                "participant_base_url": self._normalize_base_url(participant_base_url),
                "session_id": session_id,
                "username": username,
                "acquired_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
            }
        )
        self._touch_channel(channel_state)
        return self._channel_to_detail(channel_state, active_instance_base_url=participant_base_url)

    def heartbeat_field_lock(
        self,
        channel_id: str,
        *,
        snapshot_id: str,
        field_name: str,
        participant_base_url: str,
        session_id: str,
        username: str,
        selected_story_id: str | None = None,
    ) -> CollabChannelDetail:
        return self.acquire_field_lock(
            channel_id,
            snapshot_id=snapshot_id,
            field_name=field_name,
            participant_base_url=participant_base_url,
            session_id=session_id,
            username=username,
            selected_story_id=selected_story_id,
        )

    def release_field_lock(
        self,
        channel_id: str,
        *,
        snapshot_id: str,
        field_name: str,
        session_id: str,
        active_instance_base_url: str | None = None,
    ) -> CollabChannelDetail:
        channel_state = self._require_channel(channel_id)
        lock_key = self._lock_key(snapshot_id, field_name)
        channel_state["locks"] = [
            lock
            for lock in channel_state.get("locks", [])
            if not (
                self._lock_key(lock.get("snapshot_id", ""), lock.get("field_name", "")) == lock_key and lock.get("session_id") == session_id
            )
        ]
        self._touch_channel(channel_state)
        return self._channel_to_detail(channel_state, active_instance_base_url=active_instance_base_url)

    def update_story_snapshot_live(
        self,
        channel_id: str,
        snapshot_id: str,
        payload: dict[str, Any],
        *,
        participant_base_url: str,
        session_id: str,
        username: str,
        selected_story_id: str | None = None,
    ) -> CollabChannelDetail:
        channel_state = self._require_channel(channel_id)
        if channel_state["status"] != "open":
            raise ValueError("Channel is closed")
        self._upsert_presence(
            channel_state,
            session_id=session_id,
            participant_base_url=self._normalize_base_url(participant_base_url),
            username=username,
            selected_story_id=selected_story_id,
        )
        for field in ("title", "description", "summary", "comments"):
            if field in payload:
                self._assert_field_lock(channel_state, snapshot_id, field, session_id=session_id)
        self._apply_story_update(channel_state, snapshot_id, payload)
        return self._channel_to_detail(channel_state, active_instance_base_url=participant_base_url)

    def move_news_item_live(
        self,
        channel_id: str,
        source_snapshot_id: str,
        target_snapshot_id: str,
        news_item_id: str,
        *,
        participant_base_url: str,
        session_id: str,
        username: str,
    ) -> CollabChannelDetail:
        channel_state = self._require_channel(channel_id)
        if channel_state["status"] != "open":
            raise ValueError("Channel is closed")
        self._upsert_presence(
            channel_state,
            session_id=session_id,
            participant_base_url=self._normalize_base_url(participant_base_url),
            username=username,
            selected_story_id=source_snapshot_id,
        )
        self._apply_move_news_item(channel_state, source_snapshot_id, target_snapshot_id, news_item_id)
        return self._channel_to_detail(channel_state, active_instance_base_url=participant_base_url)

    def add_story_payloads(self, channel_id: str, story_payloads: list[dict[str, Any]], user: User | None = None) -> CollabChannelDetail:
        channel_state = self._require_channel(channel_id)
        if channel_state["status"] != "open":
            raise ValueError("Channel is closed")
        source_instance = self.external_base_url()
        snapshots = [self._build_snapshot_from_story(payload, source_instance) for payload in story_payloads]
        self._merge_story_snapshots(channel_state, snapshots)
        self._broadcast_update(channel_state)
        return self._channel_to_detail(channel_state)

    def add_peer_story_payloads(
        self, channel_id: str, token: str, partner_base_url: str, stories: list[dict[str, Any]]
    ) -> CollabChannelDetail:
        channel_state = self._require_channel(channel_id)
        if channel_state["status"] != "open":
            raise ValueError("Channel is closed")
        if not self._validate_token(channel_id, token):
            raise PermissionError("Invalid collaboration token")
        self._assert_known_participant(channel_state, partner_base_url)
        snapshots = [CollabStorySnapshot.model_validate(story) for story in stories]
        self._merge_story_snapshots(channel_state, snapshots)
        self._broadcast_update(channel_state, skip_participants={partner_base_url})
        return self._channel_to_detail(channel_state)

    def update_story_snapshot(self, channel_id: str, snapshot_id: str, payload: dict[str, Any]) -> CollabChannelDetail:
        channel_state = self._require_channel(channel_id)
        if channel_state["status"] != "open":
            raise ValueError("Channel is closed")
        self._apply_story_update(channel_state, snapshot_id, payload)
        self._broadcast_update(channel_state)
        return self._channel_to_detail(channel_state)

    def update_peer_story_snapshot(
        self, channel_id: str, token: str, partner_base_url: str, snapshot_id: str, payload: dict[str, Any]
    ) -> CollabChannelDetail:
        channel_state = self._require_channel(channel_id)
        if channel_state["status"] != "open":
            raise ValueError("Channel is closed")
        if not self._validate_token(channel_id, token):
            raise PermissionError("Invalid collaboration token")
        self._assert_known_participant(channel_state, partner_base_url)
        self._apply_story_update(channel_state, snapshot_id, payload)
        self._broadcast_update(channel_state, skip_participants={partner_base_url})
        return self._channel_to_detail(channel_state)

    def move_news_item(self, channel_id: str, source_snapshot_id: str, target_snapshot_id: str, news_item_id: str) -> CollabChannelDetail:
        channel_state = self._require_channel(channel_id)
        if channel_state["status"] != "open":
            raise ValueError("Channel is closed")
        self._apply_move_news_item(channel_state, source_snapshot_id, target_snapshot_id, news_item_id)
        self._broadcast_update(channel_state)
        return self._channel_to_detail(channel_state)

    def move_peer_news_item(
        self,
        channel_id: str,
        token: str,
        partner_base_url: str,
        source_snapshot_id: str,
        target_snapshot_id: str,
        news_item_id: str,
    ) -> CollabChannelDetail:
        channel_state = self._require_channel(channel_id)
        if channel_state["status"] != "open":
            raise ValueError("Channel is closed")
        if not self._validate_token(channel_id, token):
            raise PermissionError("Invalid collaboration token")
        self._assert_known_participant(channel_state, partner_base_url)
        self._apply_move_news_item(channel_state, source_snapshot_id, target_snapshot_id, news_item_id)
        self._broadcast_update(channel_state, skip_participants={partner_base_url})
        return self._channel_to_detail(channel_state)

    def close_channel(self, channel_id: str) -> CollabChannelDetail:
        channel_state = self._require_channel(channel_id)
        channel_state["status"] = "closed"
        self._touch_channel(channel_state)
        self._broadcast_update(channel_state, closed=True)
        return self._channel_to_detail(channel_state)

    def close_via_owner(self, owner_base_url: str, channel_id: str, token: str) -> CollabChannelDetail:
        response = requests.post(
            f"{self.api_root_url(owner_base_url)}/assess/collab/channels/{channel_id}/close-owner",
            json={"token": token},
            headers={"Content-type": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        detail = CollabChannelDetail.model_validate(response.json())
        self.channels[channel_id] = {**detail.model_dump(mode="json"), "token": token}
        return detail

    def finalize_channel(self, channel_id: str, user: User | None = None, story_ids: list[str] | None = None) -> CollabFinalizeResult:
        channel_state = self._require_channel(channel_id)
        selected_ids = set(story_ids or [])
        snapshots = [CollabStorySnapshot.model_validate(snapshot) for snapshot in channel_state["result_stories"]]
        if selected_ids:
            snapshots = [snapshot for snapshot in snapshots if snapshot.id in selected_ids]

        created_story_ids: list[str] = []
        for snapshot in snapshots:
            story_payload = copy.deepcopy(snapshot.story)
            story_payload.pop("id", None)
            for news_item in story_payload.get("news_items", []) or []:
                if isinstance(news_item, dict):
                    news_item.pop("id", None)
                    news_item.pop("story_id", None)
                    link = news_item.get("link") or ""
                    news_item["link"] = f"{link}#collab-{uuid.uuid4().hex}"
            result, status = Story.add(story_payload)
            if status == 200 and result.get("story_id"):
                created_story_ids.append(result["story_id"])
        return CollabFinalizeResult(channel_id=channel_id, created_story_ids=created_story_ids, report_story_ids=created_story_ids)


collaboration_service = CollaborationService()

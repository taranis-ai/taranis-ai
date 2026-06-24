import copy
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote, urlsplit

import requests
from flask import has_request_context, request
from itsdangerous import BadSignature, URLSafeSerializer
from models.assess import Story as StoryPayload
from models.collaboration import (
    CollabChannelDetail,
    CollabChannelSummary,
    CollabFinalizeResult,
    CollabInvite,
    CollabParticipant,
    CollabStorySnapshot,
    CollabWorkspaceActivityItem,
    CollabWorkspaceBriefing,
    CollabWorkspaceChatMessage,
    CollabWorkspaceComment,
    CollabWorkspaceDecision,
    CollabWorkspaceState,
    CollabWorkspaceTask,
    CollabWorkspaceTimelineEvent,
)

from core.config import Config
from core.log import logger
from core.managers.db_manager import db
from core.managers.sse_manager import sse_manager
from core.model.news_item import NewsItem
from core.model.story import Story
from core.model.user import User
from core.service.collaboration_text import StoryTextCollabService


EDITABLE_TEXT_FIELDS = ("title", "description", "summary", "comments")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CollaborationService:
    def __init__(self):
        self.channels: dict[str, dict[str, Any]] = {}
        self.serializer = URLSafeSerializer(Config.API_KEY.get_secret_value(), salt="collaboration-channel")
        self.timeout = 15
        self.lock_ttl_seconds = 10
        self.text_collab = StoryTextCollabService()

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

    @staticmethod
    def _instance_short_name(base_url: str | None) -> str | None:
        if not base_url:
            return None
        hostname = urlsplit(base_url).netloc.split("@")[-1].split(":", 1)[0]
        if not hostname:
            return None
        short = hostname.split(".", 1)[0].strip()
        return short or hostname

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
            workspace = self._ensure_workspace_state(channel_state)
            if not workspace.get("focused_story_id") and channel_state["stories"]:
                workspace["focused_story_id"] = channel_state["stories"][0].get("id")
            self._refresh_shared_docs_from_stories(channel_state)
            self._touch_channel(channel_state)
        return changed

    @staticmethod
    def _story_fields_snapshot(story_payload: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
        snapshot["title"] = story_payload.get("title")
        snapshot["description"] = story_payload.get("description")
        return snapshot

    @staticmethod
    def _doc_storage_key(snapshot_id: str, field_name: str) -> str:
        return StoryTextCollabService.doc_storage_key(snapshot_id, field_name)

    @staticmethod
    def _selection_storage_key(snapshot_id: str, field_name: str, session_id: str) -> str:
        return StoryTextCollabService.selection_storage_key(snapshot_id, field_name, session_id)

    @staticmethod
    def _story_field_text(story_payload: dict[str, Any], field_name: str) -> str:
        return str(story_payload.get(field_name) or "")

    def _ensure_shared_doc(self, channel_state: dict[str, Any], snapshot_id: str, field_name: str, text: str = "") -> dict[str, Any]:
        return self.text_collab.ensure_shared_doc(channel_state, snapshot_id, field_name, text)

    def _refresh_shared_docs_from_stories(self, channel_state: dict[str, Any]) -> None:
        runtime = self.text_collab.ensure_runtime(channel_state)
        expected_keys: set[str] = set()
        for snapshot in channel_state.get("stories", []):
            snapshot_id = snapshot.get("id", "")
            story_payload = snapshot.get("story") or {}
            for field_name in EDITABLE_TEXT_FIELDS:
                doc = self._ensure_shared_doc(
                    channel_state,
                    snapshot_id,
                    field_name,
                    self._story_field_text(story_payload, field_name),
                )
                doc["text"] = self._story_field_text(story_payload, field_name)
                expected_keys.add(self._doc_storage_key(snapshot_id, field_name))
        runtime["shared_docs"] = {key: value for key, value in self.text_collab.shared_docs(channel_state).items() if key in expected_keys}
        runtime["text_selections"] = {
            key: value
            for key, value in self.text_collab.text_selections(channel_state).items()
            if self._doc_storage_key(value.get("snapshot_id", ""), value.get("field_name", "")) in expected_keys
        }

    @staticmethod
    def _map_position_through_change(position: int, change: dict[str, Any], *, assoc: int) -> int:
        return StoryTextCollabService.map_position_through_change(position, change, assoc=assoc)

    def _rebase_changes(self, changes: list[dict[str, Any]], history: list[dict[str, Any]], version: int) -> list[dict[str, Any]]:
        return self.text_collab.rebase_changes(changes, history, version)

    @staticmethod
    def _apply_changes_to_text(text: str, changes: list[dict[str, Any]]) -> str:
        return StoryTextCollabService.apply_changes_to_text(text, changes)

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

    def _set_persisted_story_id(self, channel_state: dict[str, Any], snapshot_id: str, story_id: str) -> None:
        for key in ("stories", "result_stories"):
            for snapshot in channel_state[key]:
                if snapshot.get("id") == snapshot_id:
                    snapshot["persisted_local_story_id"] = story_id
        self._touch_channel(channel_state)

    @staticmethod
    def _find_snapshot(channel_state: dict[str, Any], snapshot_id: str) -> dict[str, Any] | None:
        for snapshot in channel_state["stories"]:
            if snapshot.get("id") == snapshot_id:
                return snapshot
        return None

    @staticmethod
    def _story_update_payload(snapshot: CollabStorySnapshot) -> dict[str, Any]:
        story_payload = copy.deepcopy(snapshot.story)
        payload: dict[str, Any] = {}
        for field in ("title", "description", "summary", "comments", "important", "read", "relevance_override"):
            if field in story_payload:
                payload[field] = story_payload.get(field)
        if "attributes" in story_payload:
            payload["attributes"] = copy.deepcopy(story_payload.get("attributes") or [])
        if "tags" in story_payload:
            payload["tags"] = copy.deepcopy(story_payload.get("tags") or [])
        return payload

    @staticmethod
    def _new_story_payload(snapshot: CollabStorySnapshot) -> dict[str, Any]:
        payload = CollaborationService._story_update_payload(snapshot)
        payload["title"] = payload.get("title") or snapshot.title or snapshot.story.get("title") or "Untitled Story"
        if created := snapshot.story.get("created") or snapshot.created:
            payload["created"] = created
        return payload

    @classmethod
    def _create_persisted_story_shell(cls, snapshot: CollabStorySnapshot, *, actor: str) -> Story:
        payload = cls._new_story_payload(snapshot)
        return Story(
            title=payload.get("title") or "Untitled Story",
            description=payload.get("description") or "",
            created=payload.get("created"),
            summary=payload.get("summary") or "",
            comments=payload.get("comments") or "",
            important=bool(payload.get("important", False)),
            read=bool(payload.get("read", False)),
            relevance_override=payload.get("relevance_override"),
            attributes=payload.get("attributes") or [],
            tags=payload.get("tags") or [],
            news_items=[],
            last_change=actor,
        )

    @staticmethod
    def _finalize_actor(user: User | None) -> str:
        return Story.last_change_for_user(user) or "internal"

    @classmethod
    def _find_matching_news_item(cls, item_data: dict[str, Any], *, prefer_item_id: bool) -> NewsItem | None:
        if prefer_item_id and (item_id := item_data.get("id")):
            if item := NewsItem.get(item_id):
                return item
        if item_hash := item_data.get("hash"):
            if item := NewsItem.get_by_hash(item_hash):
                return item
        if not prefer_item_id and (item_id := item_data.get("id")):
            return NewsItem.get(item_id)
        return None

    def _reconcile_story_news_items(
        self,
        target_story: Story,
        snapshot: CollabStorySnapshot,
        *,
        actor: str,
    ) -> None:
        desired_ids: list[str] = []
        source_stories: dict[str, Story] = {}
        prefer_item_id = snapshot.source_instance == self.external_base_url()

        for item_data in snapshot.story.get("news_items") or []:
            if not isinstance(item_data, dict):
                continue
            existing_item = self._find_matching_news_item(item_data, prefer_item_id=prefer_item_id)
            if existing_item is None:
                new_item_payload = copy.deepcopy(item_data)
                new_item_payload.pop("id", None)
                new_item_payload.pop("story_id", None)
                new_item = NewsItem.from_dict(new_item_payload)
                target_story.news_items.append(new_item)
                db.session.add(new_item)
                desired_ids.append(new_item.id)
                continue

            if existing_item.story_id != target_story.id:
                if source_story := Story.get(existing_item.story_id):
                    source_stories[source_story.id] = source_story
                    if existing_item in source_story.news_items:
                        source_story.news_items.remove(existing_item)
                target_story.news_items.append(existing_item)
            desired_ids.append(existing_item.id)

        for existing_item in target_story.news_items[:]:
            if existing_item.id in desired_ids:
                continue
            target_story.news_items.remove(existing_item)
            Story.create_from_item(existing_item, commit=False, actor=actor)

        processed_stories = {target_story, *source_stories.values()}
        for story in processed_stories:
            story.update_status(change=actor)
            story.record_revision(note="collaboration_finalize")

    def _persist_snapshot(
        self,
        channel_state: dict[str, Any],
        snapshot: CollabStorySnapshot,
        *,
        user: User | None = None,
    ) -> tuple[str, bool]:
        local_base_url = self.external_base_url()
        actor = self._finalize_actor(user)
        target_story_id: str | None = None
        created = False

        if snapshot.source_instance == local_base_url and snapshot.source_story_id and Story.get(snapshot.source_story_id):
            target_story_id = snapshot.source_story_id
        elif snapshot.persisted_local_story_id and Story.get(snapshot.persisted_local_story_id):
            target_story_id = snapshot.persisted_local_story_id

        if target_story_id is None:
            target_story = self._create_persisted_story_shell(snapshot, actor=actor)
            db.session.add(target_story)
            db.session.flush()
            target_story_id = target_story.id
            created = True
            self._set_persisted_story_id(channel_state, snapshot.id, target_story_id)
        else:
            update_result, status = Story.update(target_story_id, self._story_update_payload(snapshot), user=user, actor=actor)
            if status != 200:
                raise RuntimeError(f"Failed to update collaboration outcome story {target_story_id}: {update_result}")
            target_story = Story.get(target_story_id)
            if target_story is None:
                raise RuntimeError(f"Persisted story {target_story_id} not found")

        if created and snapshot.story.get("created"):
            target_story.created = StoryPayload.model_validate({"created": snapshot.story.get("created")}).created or target_story.created
        elif not created and (created_value := snapshot.story.get("created")):
            target_story.created = StoryPayload.model_validate({"created": created_value}).created or target_story.created

        self._reconcile_story_news_items(target_story, snapshot, actor=actor)
        db.session.commit()
        return target_story_id, created

    @staticmethod
    def _lock_key(snapshot_id: str, field_name: str) -> str:
        return f"{snapshot_id}:{field_name}"

    @staticmethod
    def _touch_channel(channel_state: dict[str, Any]) -> None:
        channel_state["updated_at"] = _utcnow().isoformat()

    @staticmethod
    def _default_workspace_state(channel_state: dict[str, Any]) -> dict[str, Any]:
        stories = channel_state.get("stories", [])
        focused_story_id = stories[0].get("id") if stories else None
        return {
            "focused_story_id": focused_story_id,
            "active_mode": "story",
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
        }

    def _ensure_workspace_state(self, channel_state: dict[str, Any]) -> dict[str, Any]:
        workspace = channel_state.get("workspace")
        if not isinstance(workspace, dict):
            workspace = self._default_workspace_state(channel_state)
            channel_state["workspace"] = workspace
        workspace.setdefault("briefing", self._default_workspace_state(channel_state)["briefing"])
        for key in ("decisions", "tasks", "comments", "chat_messages", "timeline_events", "activity_items"):
            workspace.setdefault(key, [])
        workspace.setdefault("active_mode", "story")
        workspace.setdefault("focused_story_id", workspace.get("focused_story_id") or (channel_state.get("stories") or [{}])[0].get("id"))
        return workspace

    @staticmethod
    def _workspace_item_model(target: str):
        return {
            "decision": CollabWorkspaceDecision,
            "task": CollabWorkspaceTask,
            "comment": CollabWorkspaceComment,
            "chat_message": CollabWorkspaceChatMessage,
            "timeline_event": CollabWorkspaceTimelineEvent,
            "activity_item": CollabWorkspaceActivityItem,
        }.get(target)

    @staticmethod
    def _workspace_collection_key(target: str) -> str:
        return {
            "decision": "decisions",
            "task": "tasks",
            "comment": "comments",
            "chat_message": "chat_messages",
            "timeline_event": "timeline_events",
            "activity_item": "activity_items",
        }.get(target, "")

    def _append_activity(
        self,
        channel_state: dict[str, Any],
        *,
        actor: str,
        text: str,
        participant_base_url: str | None = None,
    ) -> None:
        workspace = self._ensure_workspace_state(channel_state)
        workspace["activity_items"] = [
            {
                "id": str(uuid.uuid4()),
                "text": text,
                "actor": actor,
                "participant_base_url": participant_base_url,
                "participant_short_name": self._instance_short_name(participant_base_url),
                "created_at": _utcnow().isoformat(),
            },
            *list(workspace.get("activity_items") or []),
        ][:20]

    def _apply_workspace_patch(
        self,
        channel_state: dict[str, Any],
        payload: dict[str, Any],
        *,
        username: str,
        participant_base_url: str | None = None,
    ) -> None:
        workspace = self._ensure_workspace_state(channel_state)
        target = payload.get("target", "")
        action = payload.get("action", "")
        data = payload.get("data") or {}
        item_id = payload.get("item_id")

        if target == "workspace":
            if action != "set":
                raise ValueError("Workspace root only supports set")
            active_mode = data.get("active_mode")
            focused_story_id = data.get("focused_story_id")
            if active_mode in {"story", "briefing"}:
                workspace["active_mode"] = active_mode
            if focused_story_id:
                workspace["focused_story_id"] = focused_story_id
            self._append_activity(
                channel_state,
                actor=username,
                text="updated workspace view",
                participant_base_url=participant_base_url,
            )
            self._touch_channel(channel_state)
            return

        if target == "briefing":
            if action != "set":
                raise ValueError("Briefing only supports set")
            merged_briefing = {**(workspace.get("briefing") or {}), **data}
            workspace["briefing"] = CollabWorkspaceBriefing.model_validate(merged_briefing).model_dump(mode="json")
            self._append_activity(
                channel_state,
                actor=username,
                text="updated briefing",
                participant_base_url=participant_base_url,
            )
            self._touch_channel(channel_state)
            return

        collection_key = self._workspace_collection_key(target)
        item_model = self._workspace_item_model(target)
        if not collection_key or item_model is None:
            raise ValueError(f"Unsupported workspace patch target: {target}")

        items = list(workspace.get(collection_key) or [])
        if action == "remove":
            if not item_id:
                raise ValueError("Missing item_id for remove")
            workspace[collection_key] = [item for item in items if item.get("id") != item_id]
            self._append_activity(
                channel_state,
                actor=username,
                text=f"removed {target.replace('_', ' ')}",
                participant_base_url=participant_base_url,
            )
            self._touch_channel(channel_state)
            return

        if action != "upsert":
            raise ValueError(f"Unsupported workspace patch action: {action}")

        resolved_id = item_id or data.get("id") or str(uuid.uuid4())
        payload_data = {**data, "id": resolved_id}
        if "created_at" not in payload_data:
            payload_data["created_at"] = _utcnow().isoformat()
        if target == "chat_message":
            payload_data.setdefault("author", username)
            payload_data.setdefault("participant_base_url", participant_base_url)
            payload_data.setdefault("participant_short_name", self._instance_short_name(participant_base_url))
        if target == "task":
            payload_data.setdefault("owner", username)
            payload_data.setdefault("participant_base_url", participant_base_url)
            payload_data.setdefault("participant_short_name", self._instance_short_name(participant_base_url))
        if target == "comment":
            payload_data.setdefault("author", username)
            payload_data.setdefault("participant_base_url", participant_base_url)
            payload_data.setdefault("participant_short_name", self._instance_short_name(participant_base_url))
        item_payload = item_model.model_validate(payload_data).model_dump(mode="json")

        replaced = False
        for index, item in enumerate(items):
            if item.get("id") == resolved_id:
                items[index] = item_payload
                replaced = True
                break
        if not replaced:
            items.insert(0, item_payload)
        workspace[collection_key] = items
        self._append_activity(
            channel_state,
            actor=username,
            text=f"updated {target.replace('_', ' ')}",
            participant_base_url=participant_base_url,
        )
        self._touch_channel(channel_state)

    def _prune_runtime_state(self, channel_state: dict[str, Any]) -> None:
        runtime = self.text_collab.ensure_runtime(channel_state)
        now = _utcnow()
        valid_locks = []
        for lock in runtime.get("locks", []):
            expires_at = lock.get("expires_at")
            if not expires_at:
                continue
            try:
                if datetime.fromisoformat(expires_at) <= now:
                    continue
            except ValueError:
                continue
            valid_locks.append(lock)
        runtime["locks"] = valid_locks

    def _upsert_presence(
        self,
        channel_state: dict[str, Any],
        *,
        session_id: str,
        participant_base_url: str,
        username: str,
        selected_story_id: str | None = None,
    ) -> None:
        presence_list = self.text_collab.presence(channel_state)
        now = _utcnow().isoformat()
        for presence in presence_list:
            if presence.get("session_id") == session_id:
                presence["participant_base_url"] = participant_base_url
                presence["username"] = username
                presence["selected_story_id"] = selected_story_id
                presence["last_seen_at"] = now
                return
        presence_list.append(
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
        runtime = self.text_collab.ensure_runtime(channel_state)
        existing = runtime.get("presence", [])
        remaining = [presence for presence in existing if presence.get("session_id") != session_id]
        if len(remaining) == len(existing):
            return False
        runtime["presence"] = remaining
        runtime["locks"] = [lock for lock in runtime.get("locks", []) if lock.get("session_id") != session_id]
        runtime["text_selections"] = {
            key: value for key, value in runtime.get("text_selections", {}).items() if value.get("session_id") != session_id
        }
        self._touch_channel(channel_state)
        return True

    def _channel_to_detail(self, channel_state: dict[str, Any], active_instance_base_url: str | None = None) -> CollabChannelDetail:
        self._prune_runtime_state(channel_state)
        runtime = self.text_collab.export_runtime(channel_state)
        invite = self._build_invite(channel_state["channel_id"], channel_state["token"], channel_state["owner_base_url"])
        participants = [CollabParticipant.model_validate(item) for item in channel_state["participants"]]
        presence = list(runtime.presence)
        locks = list(runtime.locks)
        shared_docs = [
            {
                "snapshot_id": item.snapshot_id,
                "field_name": item.field_name,
                "text": item.text,
                "version": item.version,
            }
            for item in runtime.shared_docs
        ]
        text_selections = list(runtime.text_selections)
        workspace = CollabWorkspaceState.model_validate(self._ensure_workspace_state(channel_state))
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
            shared_docs=shared_docs,
            text_selections=text_selections,
            workspace=workspace,
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
        items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
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
            "runtime": {
                "presence": [],
                "locks": [],
                "shared_docs": {},
                "text_selections": {},
            },
            "workspace": {},
            "stories": [],
            "result_stories": [],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        channel_state["workspace"] = self._default_workspace_state(channel_state)
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
        self.text_collab.ensure_runtime(channel_state)
        channel_state.setdefault("workspace", self._default_workspace_state(channel_state))
        self._refresh_shared_docs_from_stories(channel_state)
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
        self.text_collab.ensure_runtime(channel_state)
        channel_state.setdefault("workspace", self._default_workspace_state(channel_state))
        self._refresh_shared_docs_from_stories(channel_state)
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
        for field in EDITABLE_TEXT_FIELDS:
            if field in payload:
                story_payload[field] = payload.get(field) or ""
        self._replace_story_snapshot(channel_state, snapshot_id, story_payload)

    def _update_story_field_text(self, channel_state: dict[str, Any], snapshot_id: str, field_name: str, text: str) -> None:
        snapshot = self._find_snapshot(channel_state, snapshot_id)
        if snapshot is None:
            raise KeyError(snapshot_id)
        story_payload = copy.deepcopy(snapshot.get("story") or {})
        story_payload[field_name] = text
        self._replace_story_snapshot(channel_state, snapshot_id, story_payload)
        doc = self._ensure_shared_doc(channel_state, snapshot_id, field_name, text)
        doc["text"] = text

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
        for lock in self.text_collab.locks(channel_state):
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
        runtime = self.text_collab.ensure_runtime(channel_state)
        runtime["locks"] = [
            lock
            for lock in runtime.get("locks", [])
            if self._lock_key(lock.get("snapshot_id", ""), lock.get("field_name", "")) != self._lock_key(snapshot_id, field_name)
        ]
        runtime["locks"].append(
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
        runtime = self.text_collab.ensure_runtime(channel_state)
        runtime["locks"] = [
            lock
            for lock in runtime.get("locks", [])
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
        self._refresh_shared_docs_from_stories(channel_state)
        return self._channel_to_detail(channel_state, active_instance_base_url=participant_base_url)

    def submit_story_ops_live(
        self,
        channel_id: str,
        *,
        snapshot_id: str,
        field_name: str,
        version: int,
        op_id: str,
        updates: list[dict[str, Any]],
        participant_base_url: str,
        session_id: str,
        username: str,
    ) -> tuple[CollabChannelDetail, dict[str, Any]]:
        channel_state = self._require_channel(channel_id)
        if channel_state["status"] != "open":
            raise ValueError("Channel is closed")
        if field_name not in EDITABLE_TEXT_FIELDS:
            raise ValueError(f"Unsupported collaboration field: {field_name}")
        self._upsert_presence(
            channel_state,
            session_id=session_id,
            participant_base_url=self._normalize_base_url(participant_base_url),
            username=username,
            selected_story_id=snapshot_id,
        )
        snapshot = self._find_snapshot(channel_state, snapshot_id)
        if snapshot is None:
            raise KeyError(snapshot_id)
        doc = self._ensure_shared_doc(
            channel_state,
            snapshot_id,
            field_name,
            self._story_field_text(snapshot.get("story") or {}, field_name),
        )
        current_version = int(doc.get("version", 0))
        if version > current_version:
            raise ValueError("Story op version is ahead of the authoritative document")
        normalized_updates = [
            {"from": int(item.get("from", 0)), "to": int(item.get("to", 0)), "insert": str(item.get("insert", ""))} for item in updates
        ]
        rebased_updates = self._rebase_changes(normalized_updates, list(doc.get("history") or []), version)
        next_text = self._apply_changes_to_text(str(doc.get("text", "")), rebased_updates)
        doc["text"] = next_text
        doc["version"] = current_version + 1
        doc.setdefault("history", []).append(
            {
                "version": doc["version"],
                "op_id": op_id,
                "session_id": session_id,
                "changes": rebased_updates,
            }
        )
        self._update_story_field_text(channel_state, snapshot_id, field_name, next_text)
        self._touch_channel(channel_state)
        detail = self._channel_to_detail(channel_state, active_instance_base_url=participant_base_url)
        return detail, {
            "snapshot_id": snapshot_id,
            "field_name": field_name,
            "version": doc["version"],
            "op_id": op_id,
            "session_id": session_id,
            "username": username,
            "updates": rebased_updates,
        }

    def update_story_selection_live(
        self,
        channel_id: str,
        *,
        snapshot_id: str,
        field_name: str,
        anchor: int,
        head: int,
        participant_base_url: str,
        session_id: str,
        username: str,
    ) -> tuple[CollabChannelDetail, dict[str, Any]]:
        channel_state = self._require_channel(channel_id)
        if field_name not in EDITABLE_TEXT_FIELDS:
            raise ValueError(f"Unsupported collaboration field: {field_name}")
        self._upsert_presence(
            channel_state,
            session_id=session_id,
            participant_base_url=self._normalize_base_url(participant_base_url),
            username=username,
            selected_story_id=snapshot_id,
        )
        selection = {
            "snapshot_id": snapshot_id,
            "field_name": field_name,
            "session_id": session_id,
            "participant_base_url": self._normalize_base_url(participant_base_url),
            "username": username,
            "anchor": max(0, int(anchor)),
            "head": max(0, int(head)),
        }
        self.text_collab.text_selections(channel_state)[self._selection_storage_key(snapshot_id, field_name, session_id)] = selection
        self._touch_channel(channel_state)
        detail = self._channel_to_detail(channel_state, active_instance_base_url=participant_base_url)
        return detail, selection

    def clear_story_selection_live(
        self,
        channel_id: str,
        *,
        snapshot_id: str,
        field_name: str,
        participant_base_url: str,
        session_id: str,
    ) -> tuple[CollabChannelDetail, dict[str, Any]]:
        channel_state = self._require_channel(channel_id)
        self.text_collab.text_selections(channel_state).pop(
            self._selection_storage_key(snapshot_id, field_name, session_id),
            None,
        )
        self._touch_channel(channel_state)
        detail = self._channel_to_detail(channel_state, active_instance_base_url=participant_base_url)
        return detail, {"snapshot_id": snapshot_id, "field_name": field_name, "session_id": session_id}

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

    def update_workspace_live(
        self,
        channel_id: str,
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
        self._apply_workspace_patch(
            channel_state,
            payload,
            username=username,
            participant_base_url=self._normalize_base_url(participant_base_url),
        )
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

        persisted_story_ids: list[str] = []
        created_story_ids: list[str] = []
        updated_story_ids: list[str] = []
        for snapshot in snapshots:
            story_id, created = self._persist_snapshot(channel_state, snapshot, user=user)
            persisted_story_ids.append(story_id)
            if created:
                created_story_ids.append(story_id)
            else:
                updated_story_ids.append(story_id)

        self._broadcast_update(channel_state)
        return CollabFinalizeResult(
            channel_id=channel_id,
            persisted_story_ids=persisted_story_ids,
            created_story_ids=created_story_ids,
            updated_story_ids=updated_story_ids,
            report_story_ids=persisted_story_ids,
        )


collaboration_service = CollaborationService()

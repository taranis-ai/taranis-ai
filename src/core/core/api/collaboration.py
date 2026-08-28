from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from urllib.parse import urlparse

import requests
from flask import Blueprint, Flask, request
from flask.views import MethodView
from flask_jwt_extended import current_user
from loro import ExportMode, VersionVector

from core.config import Config
from core.managers import queue_manager
from core.managers.auth_manager import api_key_required, auth_required
from core.managers.db_manager import db
from core.managers.realtime_publisher import realtime_publisher
from core.model.base_model import BaseModel
from core.model.collaboration_channel import CollaborationChannel
from core.model.collaboration_document import CollaborationDocument
from core.model.report_item import ReportItem
from core.model.report_item_type import ReportItemType
from core.model.story import Story
from core.service.collaboration_loro import CollaborationStore, decode, encode, token_hash


def _document(document_id: str) -> CollaborationDocument | None:
    return db.session.get(CollaborationDocument, document_id)


def _channel(channel_id: str) -> CollaborationChannel | None:
    return db.session.get(CollaborationChannel, channel_id)


def _authorized_document(row: CollaborationDocument, user, write: bool = False) -> bool:
    channel = _channel(row.channel_id)
    if not channel or channel.status != "open" and write:
        return False
    if row.resource_kind == "story":
        snapshot = next((item for item in channel.story_snapshots if item.get("id") == row.resource_id), None)
        return bool(snapshot and str(user.id) in channel.member_ids) or Story.get_for_api(row.resource_id, user)[1] == 200
    if row.resource_kind == "report":
        report = ReportItem.get(row.resource_id)
        return bool(
            report and report.access_allowed(user, write) and (not channel.report_member_ids or str(user.id) in channel.report_member_ids)
        )
    return False


def _story_snapshot(story: Story, source_instance: str, snapshot_id: str | None = None) -> dict:
    data = story.to_detail_dict()
    return {
        "id": snapshot_id or BaseModel.uuid7_str(),
        "source_instance": source_instance.rstrip("/"),
        "source_story_id": story.id,
        "persisted_local_story_id": story.id,
        "title": story.title or "",
        "description": story.description or "",
        "summary": story.summary or "",
        "comments": story.comments or "",
        "story": data,
    }


def _owner(channel: CollaborationChannel, request_host: str) -> bool:
    return channel.owner_base_url.rstrip("/") == request_host.rstrip("/")


def _touch_metadata(channel: CollaborationChannel) -> None:
    channel.metadata_version = (channel.metadata_version or 0) + 1


def _pending_operation(channel: CollaborationChannel, operation: dict, actor: str) -> dict:
    return {
        "operation_id": str(operation.get("operation_id") or BaseModel.uuid7_str()),
        "action": str(operation.get("action") or ""),
        "base_version": int(operation.get("base_version") or 0),
        "actor": actor,
        "payload": operation.get("payload") if isinstance(operation.get("payload"), dict) else {},
    }


class Channels(MethodView):
    @auth_required("ASSESS_ACCESS")
    def post(self):
        payload = request.get_json(silent=True) or {}
        story_ids = payload.get("story_ids")
        if not isinstance(story_ids, list):
            story_ids = [payload.get("story_id")]
        stories = []
        for story_id in dict.fromkeys(str(value) for value in story_ids if value):
            _, story_status = Story.get_for_api(story_id, current_user)
            story = Story.get(story_id) if story_status == 200 else None
            if story:
                stories.append(story)
        if not stories:
            return {"error": "Story is not available"}, 403
        token = token_urlsafe(32)
        channel = CollaborationChannel(
            owner_base_url=str(payload.get("owner_base_url") or request.host_url.rstrip("/")),
            owner_token_hash=token_hash(token),
            owner_token=token,
            topic=str(payload.get("topic") or "Collaboration"),
            member_ids=[str(current_user.id)],
        )
        db.session.add(channel)
        db.session.flush()
        snapshots = []
        documents = []
        for story in stories:
            snapshot = _story_snapshot(story, channel.owner_base_url)
            snapshots.append(snapshot)
            documents.append(
                CollaborationStore.document_for(
                    channel.id,
                    "story",
                    snapshot["id"],
                    initial={field: snapshot[field] for field in ("title", "description", "summary", "comments")},
                )
            )
        channel.story_snapshots = snapshots
        report_id = str(payload.get("report_id") or "")
        if report_id:
            report = ReportItem.get(report_id)
            if not report or not report.access_allowed(current_user, True):
                db.session.rollback()
                return {"error": "Report is not available"}, 403
            channel.report_member_ids = [str(current_user.id)]
            roots = (
                "title",
                *(f"attribute:{attribute.id}" for attribute in report.attributes if attribute.attribute_type.name in {"TEXT", "RICH_TEXT"}),
            )
            documents.append(
                CollaborationStore.document_for(
                    channel.id,
                    "report",
                    report.id,
                    roots,
                    initial={
                        "title": report.title or "",
                        **{
                            f"attribute:{attribute.id}": attribute.value or ""
                            for attribute in report.attributes
                            if attribute.attribute_type.name in {"TEXT", "RICH_TEXT"}
                        },
                    },
                    rich_roots={
                        f"attribute:{attribute.id}" for attribute in report.attributes if attribute.attribute_type.name == "RICH_TEXT"
                    },
                )
            )
            channel.report_drafts = [
                {
                    "id": report.id,
                    "title": report.title or "",
                    "report_item_type_id": report.report_item_type_id,
                    "status": "open",
                    "document_id": documents[-1].id,
                }
            ]
        db.session.commit()
        return {
            "channel_id": channel.id,
            "document_id": documents[0].id,
            "document_ids": [row.id for row in documents],
            "token": token,
            "owner_base_url": channel.owner_base_url,
        }, 201

    @auth_required("ASSESS_ACCESS")
    def get(self, channel_id: str | None = None):
        if channel_id is None:
            return {
                "items": [
                    {
                        "channel_id": channel.id,
                        "topic": channel.topic,
                        "story_count": len(channel.story_snapshots),
                        "status": channel.status,
                        "owner_base_url": channel.owner_base_url,
                    }
                    for channel in CollaborationChannel.query.order_by(CollaborationChannel.updated_at.desc()).all()
                ]
            }, 200
        channel = _channel(channel_id)
        if not channel:
            return {"error": "Channel not found"}, 404
        documents = CollaborationDocument.query.filter_by(channel_id=channel.id).all()
        return {
            "channel_id": channel.id,
            "status": channel.status,
            "topic": channel.topic,
            "owner_base_url": channel.owner_base_url,
            "participants": channel.participant_urls,
            "report_member_ids": channel.report_member_ids,
            "stories": channel.story_snapshots,
            "report_drafts": channel.report_drafts,
            "metadata_version": channel.metadata_version,
            "documents": [{"id": document.id, "kind": document.resource_kind, "resource_id": document.resource_id} for document in documents],
        }, 200


class Stories(MethodView):
    @auth_required("ASSESS_UPDATE")
    def post(self, channel_id: str):
        channel = _channel(channel_id)
        if not channel or channel.status != "open":
            return {"error": "Channel is not open"}, 409
        if not _owner(channel, request.host_url):
            requested = request.get_json(silent=True) or {}
            snapshots = (
                [_story_snapshot(story, request.host_url) for story in Story.query.filter(Story.id.in_(requested.get("story_ids", []))).all()]
                if isinstance(requested.get("story_ids"), list)
                else []
            )
            operation = _pending_operation(channel, requested, str(current_user.id))
            operation["action"] = "stories.add"
            operation["payload"]["snapshots"] = snapshots
            CollaborationStore().queue_operation(channel.id, operation)
            return {"queued": True, "operation_id": operation["operation_id"], "metadata_version": channel.metadata_version}, 202
        payload = request.get_json(silent=True) or {}
        story_ids = payload.get("story_ids") if isinstance(payload.get("story_ids"), list) else [payload.get("story_id")]
        existing = {item.get("source_story_id") for item in channel.story_snapshots}
        added = []
        for story_id in dict.fromkeys(str(value) for value in story_ids if value):
            if story_id in existing:
                continue
            story = Story.get(story_id)
            if not story or Story.get_for_api(story_id, current_user)[1] != 200:
                continue
            snapshot = _story_snapshot(story, channel.owner_base_url)
            channel.story_snapshots = [*channel.story_snapshots, snapshot]
            CollaborationStore.document_for(
                channel.id,
                "story",
                snapshot["id"],
                initial={field: snapshot[field] for field in ("title", "description", "summary", "comments")},
            )
            added.append(snapshot)
        if not added:
            return {"error": "No stories were added"}, 400
        _touch_metadata(channel)
        db.session.commit()
        return {"stories": added, "metadata_version": channel.metadata_version}, 200

    @auth_required("ASSESS_UPDATE")
    def delete(self, channel_id: str, snapshot_id: str):
        channel = _channel(channel_id)
        if not channel:
            return {"error": "Channel not found"}, 404
        if not _owner(channel, request.host_url):
            operation = _pending_operation(channel, request.get_json(silent=True) or {}, str(current_user.id))
            operation["action"] = "stories.remove"
            operation["payload"]["snapshot_id"] = snapshot_id
            CollaborationStore().queue_operation(channel.id, operation)
            return {"queued": True, "operation_id": operation["operation_id"], "metadata_version": channel.metadata_version}, 202
        before = len(channel.story_snapshots)
        channel.story_snapshots = [item for item in channel.story_snapshots if item.get("id") != snapshot_id]
        if len(channel.story_snapshots) == before:
            return {"error": "Story snapshot not found"}, 404
        _touch_metadata(channel)
        db.session.commit()
        return {"metadata_version": channel.metadata_version}, 200


class NewsItemMove(MethodView):
    @auth_required("ASSESS_UPDATE")
    def post(self, channel_id: str):
        channel = _channel(channel_id)
        if not channel:
            return {"error": "Channel not found"}, 404
        payload = request.get_json(silent=True) or {}
        source_id, target_id, news_item_id = (
            str(payload.get(key) or "") for key in ("source_snapshot_id", "target_snapshot_id", "news_item_id")
        )
        source = next((item for item in channel.story_snapshots if item.get("id") == source_id), None)
        target = next((item for item in channel.story_snapshots if item.get("id") == target_id), None)
        if not _owner(channel, request.host_url):
            operation = _pending_operation(channel, payload, str(current_user.id))
            operation["action"] = "news_item.move"
            operation["payload"] = {"source_snapshot_id": source_id, "target_snapshot_id": target_id, "news_item_id": news_item_id}
            operation["base_version"] = int(payload.get("base_version") or channel.metadata_version)
            CollaborationStore().queue_operation(channel.id, operation)
            return {"queued": True, "operation_id": operation["operation_id"]}, 202
        if not source or not target or source is target:
            return {"error": "Invalid story snapshots"}, 400
        items = (source.get("story") or {}).get("news_items") or []
        moved = next((item for item in items if str(item.get("id")) == news_item_id), None)
        if not moved:
            return {"error": "News item not found"}, 404
        source["story"]["news_items"] = [item for item in items if item is not moved]
        target.setdefault("story", {}).setdefault("news_items", []).append(moved)
        _touch_metadata(channel)
        db.session.commit()
        return {"metadata_version": channel.metadata_version}, 200


class PendingOperations(MethodView):
    def post(self, channel_id: str):
        channel = _channel(channel_id)
        caller = request.headers.get("X-Peer-Base-URL", "").rstrip("/")
        if not channel or token_hash(request.headers.get("X-Channel-Token", "")) != channel.owner_token_hash:
            return {"error": "Invalid channel token"}, 403
        if not caller or caller not in {channel.owner_base_url.rstrip("/"), *channel.participant_urls}:
            return {"error": "Peer is not registered"}, 403
        payload = request.get_json(silent=True) or {}
        operations = payload.get("operations") if isinstance(payload.get("operations"), list) else []
        store = CollaborationStore()
        results = []
        for raw in operations:
            operation = _pending_operation(channel, raw if isinstance(raw, dict) else {}, caller)
            if operation["base_version"] != channel.metadata_version:
                conflict = {
                    "operation_id": operation["operation_id"],
                    "action": operation["action"],
                    "proposal": operation["payload"],
                    "owner_version": channel.metadata_version,
                    "owner_state": {"stories": channel.story_snapshots, "report_drafts": channel.report_drafts},
                }
                store.add_conflict(channel.id, conflict)
                results.append({"operation_id": operation["operation_id"], "status": "conflict", "conflict": conflict})
                continue
            if operation["action"] == "stories.remove":
                snapshot_id = str(operation["payload"].get("snapshot_id") or "")
                channel.story_snapshots = [item for item in channel.story_snapshots if item.get("id") != snapshot_id]
            elif operation["action"] == "news_item.move":
                payload = operation["payload"]
                source = next((item for item in channel.story_snapshots if item.get("id") == payload.get("source_snapshot_id")), None)
                target = next((item for item in channel.story_snapshots if item.get("id") == payload.get("target_snapshot_id")), None)
                items = (source or {}).get("story", {}).get("news_items", []) if source else []
                moved = next((item for item in items if str(item.get("id")) == str(payload.get("news_item_id"))), None)
                if not source or not target or source is target or not moved:
                    results.append({"operation_id": operation["operation_id"], "status": "invalid"})
                    continue
                source["story"]["news_items"] = [item for item in items if item is not moved]
                target.setdefault("story", {}).setdefault("news_items", []).append(moved)
            elif operation["action"] == "stories.add":
                snapshots = operation["payload"].get("snapshots")
                if (
                    not isinstance(snapshots, list)
                    or not snapshots
                    or any(not isinstance(snapshot, dict) or not snapshot.get("id") for snapshot in snapshots)
                ):
                    results.append({"operation_id": operation["operation_id"], "status": "invalid"})
                    continue
                for snapshot in snapshots:
                    if any(item.get("id") == snapshot["id"] for item in channel.story_snapshots):
                        continue
                    channel.story_snapshots = [*channel.story_snapshots, snapshot]
                    CollaborationStore.document_for(
                        channel.id,
                        "story",
                        str(snapshot["id"]),
                        initial={field: str(snapshot.get(field) or "") for field in ("title", "description", "summary", "comments")},
                    )
            elif operation["action"] == "report.update":
                draft_id = str(operation["payload"].get("draft_id") or "")
                draft = next((item for item in channel.report_drafts if item.get("id") == draft_id), None)
                report = ReportItem.get(draft_id)
                if not draft or not report:
                    results.append({"operation_id": operation["operation_id"], "status": "invalid"})
                    continue
                if "title" in operation["payload"]:
                    report.title = str(operation["payload"]["title"])
                if "completed" in operation["payload"]:
                    report.completed = bool(operation["payload"]["completed"])
                if isinstance(operation["payload"].get("selected_story_ids"), list):
                    by_snapshot = {item.get("id"): item for item in channel.story_snapshots}
                    report.stories = Story.get_bulk(
                        [
                            story_id
                            for value in operation["payload"]["selected_story_ids"]
                            if str(value) in by_snapshot
                            and isinstance((story_id := by_snapshot[str(value)].get("persisted_local_story_id")), str)
                        ]
                    )
                if isinstance(operation["payload"].get("attributes"), dict):
                    for attribute in report.attributes:
                        key = f"attribute:{attribute.id}"
                        if key in operation["payload"]["attributes"]:
                            attribute.value = str(operation["payload"]["attributes"][key])
                draft.update(
                    {key: operation["payload"][key] for key in ("title", "completed", "selected_story_ids") if key in operation["payload"]}
                )
            else:
                results.append({"operation_id": operation["operation_id"], "status": "invalid"})
                continue
            _touch_metadata(channel)
            results.append({"operation_id": operation["operation_id"], "status": "applied", "metadata_version": channel.metadata_version})
        db.session.commit()
        return {"results": results, "metadata_version": channel.metadata_version}, 200

    @auth_required("ASSESS_ACCESS")
    def get(self, channel_id: str):
        if not _channel(channel_id):
            return {"error": "Channel not found"}, 404
        store = CollaborationStore()
        return {"operations": store.pending_operations(channel_id), "conflicts": store.conflicts(channel_id)}, 200


class Reconcile(MethodView):
    @auth_required("ASSESS_UPDATE")
    def post(self, channel_id: str):
        channel = _channel(channel_id)
        local_url = Config.COLLABORATION_INSTANCE_URL.rstrip("/")
        if not channel or not local_url or _owner(channel, request.host_url):
            return {"error": "Reconciliation is only available to participants"}, 400
        store = CollaborationStore()
        operations = store.pending_operations(channel_id)
        if not operations:
            return {"results": [], "conflicts": store.conflicts(channel_id)}, 200
        try:
            response = requests.post(
                f"{channel.owner_base_url.rstrip('/')}{Config.APPLICATION_ROOT}api/peer-channels/{channel_id}/metadata-sync",
                json={"operations": operations},
                headers={"X-Peer-Base-URL": local_url, "X-Channel-Token": channel.owner_token},
                timeout=(2, 10),
            )
            response.raise_for_status()
            result = response.json()
        except (requests.RequestException, ValueError):
            return {"error": "Owner is unavailable; changes remain pending"}, 503
        for item in result.get("results", []):
            if item.get("status") in {"applied", "conflict", "invalid"}:
                store.clear_pending_operation(channel_id, str(item.get("operation_id") or ""))
                if item.get("conflict"):
                    store.add_conflict(channel_id, item["conflict"])
        return {"results": result.get("results", []), "conflicts": store.conflicts(channel_id)}, 200


class ConflictResolution(MethodView):
    @auth_required("ASSESS_UPDATE")
    def post(self, channel_id: str, operation_id: str):
        channel = _channel(channel_id)
        if not channel:
            return {"error": "Channel not found"}, 404
        store = CollaborationStore()
        conflict = next((item for item in store.conflicts(channel_id) if item.get("operation_id") == operation_id), None)
        if not conflict:
            return {"error": "Conflict not found"}, 404
        payload = request.get_json(silent=True) or {}
        resolved = payload.get("payload") if isinstance(payload.get("payload"), dict) else conflict.get("proposal", {})
        operation = _pending_operation(
            channel,
            {
                "operation_id": BaseModel.uuid7_str(),
                "action": conflict.get("action"),
                "base_version": channel.metadata_version,
                "payload": resolved,
            },
            str(current_user.id),
        )
        store.queue_operation(channel.id, operation)
        store.resolve_conflict(channel.id, operation_id)
        return {"queued": True, "operation_id": operation["operation_id"], "metadata_version": channel.metadata_version}, 202


class ReportWorkspace(MethodView):
    @auth_required("ANALYZE_ACCESS")
    def get(self, channel_id: str):
        channel = _channel(channel_id)
        if not channel:
            return {"error": "Channel not found"}, 404
        reports = ReportItem.get_all_for_api(filter_args={}, with_count=False, user=current_user)
        report_types = ReportItemType.get_all_for_user_api(current_user)
        return {
            "candidates": reports,
            "report_types": report_types,
            "drafts": channel.report_drafts,
            "members": channel.report_member_ids,
        }, 200

    @auth_required("ASSESS_UPDATE")
    def put(self, channel_id: str):
        channel = _channel(channel_id)
        if not channel or not _owner(channel, request.host_url):
            return {"error": "Only the channel owner can change report members"}, 403
        payload = request.get_json(silent=True) or {}
        members = payload.get("member_ids")
        if not isinstance(members, list) or any(not str(value) for value in members):
            return {"error": "Invalid report members"}, 400
        channel.report_member_ids = list(dict.fromkeys(str(value) for value in members))
        _touch_metadata(channel)
        db.session.commit()
        return {"members": channel.report_member_ids, "metadata_version": channel.metadata_version}, 200


class ReportDrafts(MethodView):
    @auth_required("ASSESS_UPDATE")
    def post(self, channel_id: str):
        channel = _channel(channel_id)
        if not channel or channel.status != "open" or not _owner(channel, request.host_url):
            return {"error": "Only the channel owner can create report drafts"}, 403
        payload = request.get_json(silent=True) or {}
        report_type_id = str(payload.get("report_item_type_id") or "")
        report_data = {"title": str(payload.get("title") or ""), "report_item_type_id": report_type_id, "stories": []}
        report, status = ReportItem.add(report_data, current_user)
        if status != 200 or not isinstance(report, ReportItem):
            return report, status
        roots = (
            "title",
            *(f"attribute:{attribute.id}" for attribute in report.attributes if attribute.attribute_type.name in {"TEXT", "RICH_TEXT"}),
        )
        document = CollaborationStore.document_for(
            channel.id,
            "report",
            report.id,
            roots,
            initial={
                "title": report.title or "",
                **{
                    f"attribute:{attribute.id}": attribute.value or ""
                    for attribute in report.attributes
                    if attribute.attribute_type.name in {"TEXT", "RICH_TEXT"}
                },
            },
            rich_roots={f"attribute:{attribute.id}" for attribute in report.attributes if attribute.attribute_type.name == "RICH_TEXT"},
        )
        draft = {
            "id": report.id,
            "title": report.title or "",
            "report_item_type_id": report.report_item_type_id,
            "status": "open",
            "document_id": document.id,
        }
        channel.report_drafts = [*channel.report_drafts, draft]
        _touch_metadata(channel)
        db.session.commit()
        return {"draft": draft}, 201

    @auth_required("ASSESS_UPDATE")
    def delete(self, channel_id: str, draft_id: str):
        channel = _channel(channel_id)
        if not channel or not _owner(channel, request.host_url):
            return {"error": "Only the channel owner can delete report drafts"}, 403
        draft = next((item for item in channel.report_drafts if item.get("id") == draft_id), None)
        if not draft:
            return {"error": "Report draft not found"}, 404
        channel.report_drafts = [item for item in channel.report_drafts if item.get("id") != draft_id]
        report = ReportItem.get(draft_id)
        if report:
            db.session.delete(report)
        _touch_metadata(channel)
        db.session.commit()
        return {}, 204

    @auth_required("ASSESS_UPDATE")
    def patch(self, channel_id: str, draft_id: str):
        channel = _channel(channel_id)
        payload = request.get_json(silent=True) or {}
        if not channel:
            return {"error": "Channel not found"}, 404
        if not _owner(channel, request.host_url):
            operation = _pending_operation(channel, payload, str(current_user.id))
            operation["action"] = "report.update"
            operation["payload"]["draft_id"] = draft_id
            CollaborationStore().queue_operation(channel.id, operation)
            return {"queued": True, "operation_id": operation["operation_id"]}, 202
        report = ReportItem.get(draft_id)
        draft = next((item for item in channel.report_drafts if item.get("id") == draft_id), None)
        if not report or not draft:
            return {"error": "Report draft not found"}, 404
        if "title" in payload:
            report.title = str(payload["title"])
        if "completed" in payload:
            report.completed = bool(payload["completed"])
        if "selected_story_ids" in payload and isinstance(payload["selected_story_ids"], list):
            allowed = {item.get("id"): item for item in channel.story_snapshots}
            report.stories = Story.get_bulk(
                [
                    story_id
                    for value in payload["selected_story_ids"]
                    if str(value) in allowed and isinstance((story_id := allowed[str(value)].get("persisted_local_story_id")), str)
                ]
            )
        if isinstance(payload.get("attributes"), dict):
            for attribute in report.attributes:
                key = f"attribute:{attribute.id}"
                if key in payload["attributes"]:
                    attribute.value = str(payload["attributes"][key])
        draft.update({key: payload[key] for key in ("title", "completed", "selected_story_ids") if key in payload})
        _touch_metadata(channel)
        db.session.commit()
        return {"draft": draft, "metadata_version": channel.metadata_version}, 200


class ReportDraftFinalize(MethodView):
    @auth_required("ASSESS_UPDATE")
    def post(self, channel_id: str, draft_id: str):
        channel = _channel(channel_id)
        draft = next((item for item in channel.report_drafts if item.get("id") == draft_id), None) if channel else None
        document = (
            CollaborationDocument.query.filter_by(channel_id=channel_id, resource_kind="report", resource_id=draft_id).first()
            if channel
            else None
        )
        if not channel or not draft or not document or not _owner(channel, request.host_url):
            return {"error": "Report draft not found"}, 404
        try:
            store = CollaborationStore()
            if store.conflicts(channel.id):
                return {"error": "Unresolved collaboration conflicts remain"}, 409
            if not store.checkpoint(document):
                return {"error": "Checkpoint is busy"}, 409
            report = ReportItem.get(draft_id)
            if not report:
                return {"error": "Report draft not found"}, 404
            values = store.text_values(document)
            report.title = values.get("title", report.title)
            for attribute in report.attributes:
                root = f"attribute:{attribute.id}"
                if root in values:
                    attribute.value = (
                        store.rich_text_value(document, root)[0] if attribute.attribute_type.name == "RICH_TEXT" else values[root]
                    )
            if not report.title.strip() or any(attribute.required and not (attribute.value or "").strip() for attribute in report.attributes):
                return {"error": "Required report fields are missing"}, 400
            report.completed = True
            report.revision += 1
            report.record_revision(current_user, note="collaboration_finalize")
            draft["status"] = "finalized"
            _touch_metadata(channel)
            db.session.commit()
        except Exception:
            db.session.rollback()
            return {"error": "Report finalization failed"}, 503
        return {"draft": draft}, 200


class ChannelJoin(MethodView):
    @auth_required("ASSESS_ACCESS")
    def post(self):
        payload = request.get_json(silent=True) or {}
        channel_id = str(payload.get("channel_id") or "")
        channel = _channel(channel_id)
        token = str(payload.get("token") or "")
        owner_base_url = str(payload.get("owner_base_url") or "").rstrip("/")
        if not channel and owner_base_url and urlparse(owner_base_url).scheme in {"http", "https"}:
            try:
                response = requests.post(
                    f"{owner_base_url}{Config.APPLICATION_ROOT}api/peer-channels/{channel_id}/register",
                    json={"base_url": request.host_url.rstrip("/"), "token": token},
                    timeout=(2, 5),
                )
                remote = response.json() if response.ok else None
            except (requests.RequestException, ValueError):
                remote = None
            if isinstance(remote, dict) and remote.get("channel_id") == channel_id:
                channel = CollaborationChannel(
                    id=channel_id,
                    owner_base_url=owner_base_url,
                    owner_token_hash=token_hash(token),
                    owner_token=token,
                    topic=str(remote.get("topic") or "Collaboration"),
                    story_snapshots=remote.get("stories") if isinstance(remote.get("stories"), list) else [],
                    report_drafts=remote.get("report_drafts") if isinstance(remote.get("report_drafts"), list) else [],
                    report_member_ids=remote.get("report_member_ids") if isinstance(remote.get("report_member_ids"), list) else [],
                    metadata_version=int(remote.get("metadata_version") or 0),
                    member_ids=[str(current_user.id)],
                )
                db.session.add(channel)
                for item in remote.get("documents", []):
                    if isinstance(item, dict) and item.get("id") and item.get("kind") and item.get("resource_id"):
                        CollaborationStore.document_for(
                            channel_id,
                            str(item["kind"]),
                            str(item["resource_id"]),
                            tuple(item.get("roots") or ("title",)),
                            document_id=str(item["id"]),
                            initial=item.get("initial_values") if isinstance(item.get("initial_values"), dict) else None,
                            rich_roots=set(item.get("rich_roots") or ()),
                        )
                db.session.commit()
                for item in remote.get("documents", []):
                    if not isinstance(item, dict) or not item.get("id"):
                        continue
                    local_document = _document(str(item["id"]))
                    if not local_document:
                        continue
                    try:
                        sync_response = requests.post(
                            f"{owner_base_url}{Config.APPLICATION_ROOT}api/peer-documents/{local_document.id}/sync",
                            json={"version_vector": encode(VersionVector().encode())},
                            headers={"X-Peer-Base-URL": request.host_url.rstrip("/"), "X-Channel-Token": token},
                            timeout=(2, 10),
                        )
                        update = sync_response.json().get("update") if sync_response.ok else None
                        if update:
                            CollaborationStore().accept(local_document, decode(update), f"join:{channel_id}:{local_document.id}")
                    except (requests.RequestException, ValueError):
                        continue
        if not channel or not token or token_hash(token) != channel.owner_token_hash:
            return {"error": "Invalid collaboration invitation"}, 403
        base_url = str(payload.get("base_url") or request.host_url.rstrip("/"))
        if str(current_user.id) not in channel.member_ids:
            channel.member_ids = [*channel.member_ids, str(current_user.id)]
        if base_url not in channel.participant_urls:
            channel.participant_urls = [*channel.participant_urls, base_url]
            db.session.commit()
        return {"channel_id": channel.id, "owner_base_url": channel.owner_base_url, "status": channel.status}, 200


class PeerChannelRegister(MethodView):
    def post(self, channel_id: str):
        payload = request.get_json(silent=True) or {}
        channel = _channel(channel_id)
        if not channel or token_hash(str(payload.get("token") or "")) != channel.owner_token_hash:
            return {"error": "Invalid channel invitation"}, 403
        base_url = str(payload.get("base_url") or "").rstrip("/")
        if not base_url:
            return {"error": "Peer URL is required"}, 400
        if base_url not in channel.participant_urls:
            channel.participant_urls = [*channel.participant_urls, base_url]
            db.session.commit()
        documents = CollaborationDocument.query.filter_by(channel_id=channel.id).all()
        return {
            "channel_id": channel.id,
            "topic": channel.topic,
            "stories": channel.story_snapshots,
            "report_drafts": channel.report_drafts,
            "report_member_ids": channel.report_member_ids,
            "metadata_version": channel.metadata_version,
            "documents": [
                {
                    "id": row.id,
                    "kind": row.resource_kind,
                    "resource_id": row.resource_id,
                    "roots": row.root_names,
                    "rich_roots": row.rich_roots,
                    "initial_values": row.initial_values,
                }
                for row in documents
            ],
        }, 200


class PeerSync(MethodView):
    def post(self, document_id: str):
        row = _document(document_id)
        if not row:
            return {"error": "Document not found"}, 404
        channel = _channel(row.channel_id)
        caller = request.headers.get("X-Peer-Base-URL", "").rstrip("/")
        if not channel or not caller or caller not in {channel.owner_base_url.rstrip("/"), *channel.participant_urls}:
            return {"error": "Peer is not registered"}, 403
        if token_hash(request.headers.get("X-Channel-Token", "")) != channel.owner_token_hash:
            return {"error": "Invalid channel token"}, 403
        payload = request.get_json(silent=True) or {}
        try:
            version_vector = decode(payload["version_vector"])
            update = decode(payload["update"]) if payload.get("update") else None
            store = CollaborationStore()
            if update:
                stream_id, _ = store.accept(row, update, f"peer:{caller}:{payload.get('update_id', '')}")
                realtime_publisher.publish(
                    f"collab:{row.id}",
                    "collab.document.update",
                    "updated",
                    data={"document_id": row.id, "update_id": stream_id, "update": encode(update)},
                )
                if Config.COLLABORATION_INSTANCE_URL and channel and hasattr(queue_manager, "queue_manager"):
                    for peer in (set(channel.participant_urls) | {channel.owner_base_url}) - {
                        caller,
                        Config.COLLABORATION_INSTANCE_URL.rstrip("/"),
                    }:
                        queue_manager.queue_manager.enqueue_task(
                            "misc",
                            "federate_collaboration_document",
                            row.id,
                            peer,
                            channel.owner_token,
                            job_id=f"collab-federate-{row.id}-{token_hash(peer)[:16]}",
                        )
            missing = store.sync(row, version_vector)
        except (KeyError, ValueError):
            return {"error": "Invalid peer synchronization payload"}, 400
        except Exception:
            return {"error": "Collaboration storage unavailable"}, 503
        return {"update": encode(missing)}, 200


class Finalize(MethodView):
    @auth_required("ASSESS_UPDATE")
    def post(self, channel_id: str):
        channel = _channel(channel_id)
        if not channel or channel.status != "open":
            return {"error": "Channel is not open"}, 409
        if channel.owner_base_url.rstrip("/") != request.host_url.rstrip("/"):
            return {"error": "Only the channel owner can finalize"}, 403
        store = CollaborationStore()
        documents = CollaborationDocument.query.filter_by(channel_id=channel.id).all()
        try:
            local_url = Config.COLLABORATION_INSTANCE_URL.rstrip("/") or request.host_url.rstrip("/")
            for peer in set(channel.participant_urls) - {local_url}:
                if any(not store.synchronize_with_peer(document, peer, channel.owner_token) for document in documents):
                    return {"error": "A participant is unreachable or not synchronized"}, 409
            for document in documents:
                if not store.checkpoint(document):
                    return {"error": "Checkpoint is busy"}, 409
                if document.resource_kind == "story":
                    values = store.text_values(document)
                    snapshot = next((item for item in channel.story_snapshots if item.get("id") == document.resource_id), {})
                    story = Story.get(snapshot.get("persisted_local_story_id") or snapshot.get("source_story_id"))
                    if story:
                        for field, value in values.items():
                            setattr(story, field, value)
                            snapshot[field] = value
                        snapshot["story"] = story.to_detail_dict()
                        if not story.title.strip():
                            db.session.rollback()
                            return {"error": "Story title is required"}, 400
                        story.revision += 1
                        story.updated = datetime.now(UTC).replace(tzinfo=None)
                elif document.resource_kind == "report":
                    report = ReportItem.get(document.resource_id)
                    if report:
                        values = store.text_values(document)
                        report.title = values.get("title", report.title)
                        for attribute in report.attributes:
                            root = f"attribute:{attribute.id}"
                            if root in values:
                                attribute.value = (
                                    store.rich_text_value(document, root)[0] if attribute.attribute_type.name == "RICH_TEXT" else values[root]
                                )
                        if not report.title.strip() or any(
                            attribute.required and not (attribute.value or "").strip() for attribute in report.attributes
                        ):
                            db.session.rollback()
                            return {"error": "Required report fields are missing"}, 400
                        report.revision += 1
                        report.last_updated = datetime.now(UTC).replace(tzinfo=None)
            channel.story_snapshots = channel.story_snapshots
            channel.metadata_version += 1
            channel.status = "closed"
            db.session.commit()
        except Exception:
            db.session.rollback()
            return {"error": "Finalization failed"}, 503
        realtime_publisher.publish(f"collab:{channel.id}", "collab.document.closed", "closed", data={"channel_id": channel.id})
        return {"channel_id": channel.id, "status": channel.status}, 200


class Close(MethodView):
    @auth_required("ASSESS_UPDATE")
    def post(self, channel_id: str):
        channel = _channel(channel_id)
        if not channel:
            return {"error": "Channel not found"}, 404
        if channel.owner_base_url.rstrip("/") != request.host_url.rstrip("/"):
            return {"error": "Only the channel owner can close"}, 403
        channel.status = "closed"
        db.session.commit()
        realtime_publisher.publish(f"collab:{channel.id}", "collab.document.closed", "closed", data={"channel_id": channel.id})
        return {"channel_id": channel.id, "status": channel.status}, 200


class Document(MethodView):
    @auth_required()
    def get(self, document_id: str):
        row = _document(document_id)
        if not row or not _authorized_document(row, current_user):
            return {"error": "Document not found"}, 404
        store = CollaborationStore()
        try:
            materialized = store.load(row)
        except Exception:
            return {"error": "Collaboration storage unavailable"}, 503
        report = ReportItem.get(row.resource_id) if row.resource_kind == "report" else None
        channel = _channel(row.channel_id)
        story = (
            next((item for item in channel.story_snapshots if item.get("id") == row.resource_id), None)
            if channel and row.resource_kind == "story"
            else None
        )
        return {
            "document_id": row.id,
            "channel_id": row.channel_id,
            "resource_kind": row.resource_kind,
            "resource_id": row.resource_id,
            "schema_version": row.schema_version,
            "snapshot": encode(materialized.document.export(ExportMode.Snapshot())),
            "version_vector": encode(materialized.document.oplog_vv.encode()),
            "presence": store.presence(row.id),
            "fields": row.root_names or (["title", "description", "summary", "comments"] if row.resource_kind == "story" else ["title"]),
            "rich_fields": row.rich_roots
            or (
                []
                if row.resource_kind == "story" or not report
                else [f"attribute:{attribute.id}" for attribute in report.attributes if attribute.attribute_type.name == "RICH_TEXT"]
            ),
            "initial_fields": row.initial_values or {},
            "field_types": {}
            if row.resource_kind == "story" or not report
            else {f"attribute:{attribute.id}": attribute.attribute_type.name for attribute in report.attributes},
            "scalar_fields": {}
            if row.resource_kind == "story" or not report
            else {
                f"attribute:{attribute.id}": {"type": attribute.attribute_type.name, "value": attribute.value or ""}
                for attribute in report.attributes
                if attribute.attribute_type.name not in {"TEXT", "RICH_TEXT"}
            },
            "story": story or {},
            "report": {"id": report.id, "title": report.title, "completed": report.completed} if report else None,
        }, 200

    @auth_required("ASSESS_UPDATE")
    def post(self, document_id: str):
        row = _document(document_id)
        if not row or not _authorized_document(row, current_user, True):
            return {"error": "Document not found"}, 404
        body = request.get_data()
        if request.mimetype != "application/octet-stream":
            return {"error": "application/octet-stream is required"}, 415
        if not request.headers.get("X-Update-ID"):
            return {"error": "X-Update-ID is required"}, 400
        try:
            stream_id, version = CollaborationStore().accept(row, body, request.headers.get("X-Update-ID", ""))
        except ValueError:
            return {"error": "Invalid collaboration update"}, 400
        except Exception:
            return {"error": "Collaboration storage unavailable"}, 503
        realtime_publisher.publish(
            f"collab:{row.id}",
            "collab.document.update",
            "updated",
            data={"document_id": row.id, "update_id": stream_id, "update": encode(body)},
        )
        if hasattr(queue_manager, "queue_manager"):
            queue_manager.queue_manager.enqueue_at(
                "misc",
                "checkpoint_collaboration_document",
                datetime.now(UTC) + timedelta(seconds=30),
                row.id,
                job_id=f"collab-checkpoint-{row.id}",
            )
            channel = _channel(row.channel_id)
            local_url = Config.COLLABORATION_INSTANCE_URL.rstrip("/")
            if channel and local_url:
                peers = set(channel.participant_urls) | {channel.owner_base_url}
                for peer in peers - {local_url}:
                    queue_manager.queue_manager.enqueue_task(
                        "misc",
                        "federate_collaboration_document",
                        row.id,
                        peer,
                        channel.owner_token,
                        job_id=f"collab-federate-{row.id}-{token_hash(peer)[:16]}",
                    )
        return {"update_id": stream_id, "version_vector": encode(version)}, 202


class Checkpoint(MethodView):
    @api_key_required
    def post(self, document_id: str):
        row = _document(document_id)
        if not row:
            return {"error": "Document not found"}, 404
        try:
            if not CollaborationStore().checkpoint(row):
                return {"error": "Checkpoint is busy"}, 409
        except Exception:
            return {"error": "Checkpoint failed"}, 503
        return {"checkpointed": True}, 200


class Federate(MethodView):
    @api_key_required
    def post(self, document_id: str):
        row = _document(document_id)
        payload = request.get_json(silent=True) or {}
        if not row or not isinstance(payload.get("peer_url"), str) or not isinstance(payload.get("token"), str):
            return {"error": "Invalid federation request"}, 400
        if CollaborationStore().synchronize_with_peer(row, payload["peer_url"], payload["token"]):
            return {"synchronized": True}, 200
        return {"error": "Peer synchronization failed"}, 503


class Sync(MethodView):
    @auth_required()
    def post(self, document_id: str):
        row = _document(document_id)
        if not row or not _authorized_document(row, current_user):
            return {"error": "Document not found"}, 404
        payload = request.get_json(silent=True) or {}
        try:
            missing = CollaborationStore().sync(
                row, decode(payload["version_vector"]), decode(payload["update"]) if payload.get("update") else None
            )
        except (KeyError, ValueError):
            return {"error": "Invalid version vector"}, 400
        except Exception:
            return {"error": "Collaboration storage unavailable"}, 503
        return {"update": encode(missing)}, 200


class Presence(MethodView):
    @auth_required("ASSESS_UPDATE")
    def put(self, document_id: str, session_id: str):
        row = _document(document_id)
        if not row or not _authorized_document(row, current_user, True):
            return {"error": "Document not found"}, 404
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return {"error": "Invalid presence"}, 400
        payload = {key: value for key, value in payload.items() if key not in {"session_id", "user_id", "name"}}
        payload.update({"session_id": session_id, "user_id": str(current_user.id), "name": str(current_user.username)})
        try:
            CollaborationStore().set_presence(document_id, session_id, payload)
        except Exception:
            return {"error": "Collaboration storage unavailable"}, 503
        realtime_publisher.publish(f"collab:{document_id}", "collab.presence.update", "updated", data=payload)
        return {}, 204

    @auth_required("ASSESS_UPDATE")
    def delete(self, document_id: str, session_id: str):
        row = _document(document_id)
        if not row or not _authorized_document(row, current_user, True):
            return {"error": "Document not found"}, 404
        try:
            CollaborationStore().delete_presence(document_id, session_id)
        except Exception:
            return {"error": "Collaboration storage unavailable"}, 503
        realtime_publisher.publish(f"collab:{document_id}", "collab.presence.left", "deleted", data={"session_id": session_id})
        return {}, 204


def initialize(app: Flask):
    bp = Blueprint("collaboration", __name__, url_prefix=f"{app.config['APPLICATION_ROOT']}api")
    bp.add_url_rule("/collaboration/channels", view_func=Channels.as_view("channels"), methods=["POST"])
    bp.add_url_rule("/collaboration/channels", view_func=Channels.as_view("channel_list"), methods=["GET"])
    bp.add_url_rule("/collaboration/channels/<string:channel_id>", view_func=Channels.as_view("channel"), methods=["GET"])
    bp.add_url_rule("/collaboration/channels/<string:channel_id>/stories", view_func=Stories.as_view("stories"), methods=["POST"])
    bp.add_url_rule(
        "/collaboration/channels/<string:channel_id>/stories/<string:snapshot_id>", view_func=Stories.as_view("story"), methods=["DELETE"]
    )
    bp.add_url_rule(
        "/collaboration/channels/<string:channel_id>/pending-operations",
        view_func=PendingOperations.as_view("pending_operations"),
        methods=["GET"],
    )
    bp.add_url_rule("/collaboration/channels/<string:channel_id>/reconcile", view_func=Reconcile.as_view("reconcile"), methods=["POST"])
    bp.add_url_rule(
        "/collaboration/channels/<string:channel_id>/conflicts/<string:operation_id>/resolve",
        view_func=ConflictResolution.as_view("conflict_resolution"),
        methods=["POST"],
    )
    bp.add_url_rule(
        "/collaboration/channels/<string:channel_id>/move-news-item", view_func=NewsItemMove.as_view("news_item_move"), methods=["POST"]
    )
    bp.add_url_rule(
        "/collaboration/channels/<string:channel_id>/report-workspace",
        view_func=ReportWorkspace.as_view("report_workspace"),
        methods=["GET", "PUT"],
    )
    bp.add_url_rule(
        "/collaboration/channels/<string:channel_id>/report-drafts", view_func=ReportDrafts.as_view("report_drafts"), methods=["POST"]
    )
    bp.add_url_rule(
        "/collaboration/channels/<string:channel_id>/report-drafts/<string:draft_id>",
        view_func=ReportDrafts.as_view("report_draft"),
        methods=["DELETE", "PATCH"],
    )
    bp.add_url_rule(
        "/collaboration/channels/<string:channel_id>/report-drafts/<string:draft_id>/finalize",
        view_func=ReportDraftFinalize.as_view("report_draft_finalize"),
        methods=["POST"],
    )
    bp.add_url_rule("/collaboration/channels/join", view_func=ChannelJoin.as_view("channel_join"), methods=["POST"])
    bp.add_url_rule(
        "/peer-channels/<string:channel_id>/register", view_func=PeerChannelRegister.as_view("peer_channel_register"), methods=["POST"]
    )
    bp.add_url_rule(
        "/peer-channels/<string:channel_id>/metadata-sync", view_func=PendingOperations.as_view("peer_metadata_sync"), methods=["POST"]
    )
    bp.add_url_rule("/peer-documents/<string:document_id>/sync", view_func=PeerSync.as_view("peer_document_sync"), methods=["POST"])
    bp.add_url_rule("/collaboration/channels/<string:channel_id>/finalize", view_func=Finalize.as_view("finalize"), methods=["POST"])
    bp.add_url_rule("/collaboration/channels/<string:channel_id>/close", view_func=Close.as_view("close"), methods=["POST"])
    bp.add_url_rule("/documents/<string:document_id>", view_func=Document.as_view("document"), methods=["GET"])
    bp.add_url_rule("/documents/<string:document_id>/updates", view_func=Document.as_view("document_update"), methods=["POST"])
    bp.add_url_rule("/documents/<string:document_id>/checkpoint", view_func=Checkpoint.as_view("document_checkpoint"), methods=["POST"])
    bp.add_url_rule("/documents/<string:document_id>/federate", view_func=Federate.as_view("document_federate"), methods=["POST"])
    bp.add_url_rule("/documents/<string:document_id>/sync", view_func=Sync.as_view("document_sync"), methods=["POST"])
    bp.add_url_rule(
        "/documents/<string:document_id>/presence/<string:session_id>", view_func=Presence.as_view("presence"), methods=["PUT", "DELETE"]
    )
    app.register_blueprint(bp)

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
from core.model.collaboration_channel import CollaborationChannel
from core.model.collaboration_document import CollaborationDocument
from core.model.report_item import ReportItem
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
        return Story.get_for_api(row.resource_id, user)[1] == 200 or str(user.id) in channel.member_ids
    if row.resource_kind == "report":
        report = ReportItem.get(row.resource_id)
        return bool(
            report and report.access_allowed(user, write) and (not channel.report_member_ids or str(user.id) in channel.report_member_ids)
        )
    return False


class Channels(MethodView):
    @auth_required("ASSESS_ACCESS")
    def post(self):
        payload = request.get_json(silent=True) or {}
        story_id = str(payload.get("story_id") or "")
        _, story_status = Story.get_for_api(story_id, current_user)
        story = Story.get(story_id) if story_status == 200 else None
        if not story:
            return {"error": "Story is not available"}, 403
        token = token_urlsafe(32)
        channel = CollaborationChannel(
            owner_base_url=str(payload.get("owner_base_url") or request.host_url.rstrip("/")),
            owner_token_hash=token_hash(token),
            owner_token=token,
            member_ids=[str(current_user.id)],
        )
        db.session.add(channel)
        db.session.flush()
        document = CollaborationStore.document_for(
            channel.id,
            "story",
            story.id,
            initial={field: getattr(story, field) or "" for field in ("title", "description", "summary", "comments")},
        )
        report_id = str(payload.get("report_id") or "")
        if report_id:
            report = ReportItem.get(report_id)
            if not report or not report.access_allowed(current_user, True):
                db.session.rollback()
                return {"error": "Report is not available"}, 403
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
            )
        db.session.commit()
        return {"channel_id": channel.id, "document_id": document.id, "token": token, "owner_base_url": channel.owner_base_url}, 201

    @auth_required("ASSESS_ACCESS")
    def get(self, channel_id: str | None = None):
        if channel_id is None:
            return {
                "items": [
                    {"channel_id": channel.id, "status": channel.status, "owner_base_url": channel.owner_base_url}
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
            "owner_base_url": channel.owner_base_url,
            "participants": channel.participant_urls,
            "documents": [{"id": document.id, "kind": document.resource_kind, "resource_id": document.resource_id} for document in documents],
        }, 200


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
                    member_ids=[str(current_user.id)],
                )
                db.session.add(channel)
                for item in remote.get("documents", []):
                    if isinstance(item, dict) and item.get("id") and item.get("kind") and item.get("resource_id"):
                        CollaborationStore.document_for(channel_id, str(item["kind"]), str(item["resource_id"]), document_id=str(item["id"]))
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
            "documents": [{"id": row.id, "kind": row.resource_kind, "resource_id": row.resource_id} for row in documents],
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
                    story = Story.get(document.resource_id)
                    if story:
                        for field, value in values.items():
                            setattr(story, field, value)
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
        return {
            "document_id": row.id,
            "resource_kind": row.resource_kind,
            "resource_id": row.resource_id,
            "schema_version": row.schema_version,
            "snapshot": encode(materialized.document.export(ExportMode.Snapshot())),
            "version_vector": encode(materialized.document.oplog_vv.encode()),
            "presence": store.presence(row.id),
            "fields": ["title", "description", "summary", "comments"]
            if row.resource_kind == "story"
            else [
                "title",
                *(f"attribute:{attribute.id}" for attribute in report.attributes if attribute.attribute_type.name in {"TEXT", "RICH_TEXT"}),
            ]
            if report
            else ["title"],
            "rich_fields": []
            if row.resource_kind == "story" or not report
            else [f"attribute:{attribute.id}" for attribute in report.attributes if attribute.attribute_type.name == "RICH_TEXT"],
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
    bp.add_url_rule("/collaboration/channels/join", view_func=ChannelJoin.as_view("channel_join"), methods=["POST"])
    bp.add_url_rule(
        "/peer-channels/<string:channel_id>/register", view_func=PeerChannelRegister.as_view("peer_channel_register"), methods=["POST"]
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

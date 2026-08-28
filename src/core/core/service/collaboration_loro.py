import base64
import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, cast

import requests
from loro import ExportMode, LoroDoc, VersionVector
from redis import Redis
from redis.exceptions import RedisError

from core.config import Config
from core.managers.db_manager import db
from core.model.collaboration_document import CollaborationDocument


MAX_UPDATE_BYTES = 512 * 1024
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
PREFIX = "taranis:collab:"
PRESENCE_TTL = 60


@dataclass
class Materialized:
    document: LoroDoc
    stream_id: str


class CollaborationStore:
    def __init__(self, redis: Redis | None = None):
        self.redis = redis or Redis.from_url(
            Config.REDIS_URL, password=Config.REDIS_PASSWORD.get_secret_value() if Config.REDIS_PASSWORD else None
        )
        self.cache: OrderedDict[str, Materialized] = OrderedDict()

    @staticmethod
    def _key(document_id: str, suffix: str) -> str:
        return f"{PREFIX}{document_id}:{suffix}"

    @staticmethod
    def create_document(
        channel_id: str,
        resource_kind: str,
        resource_id: str,
        roots: tuple[str, ...] | None = None,
        initial: dict[str, str] | None = None,
        rich_roots: set[str] | None = None,
    ) -> CollaborationDocument:
        document = LoroDoc()
        roots = roots or (("title", "description", "summary", "comments") if resource_kind == "story" else ("title",))
        for root in roots:
            if rich_roots and root in rich_roots:
                document.get_map(root)
                continue
            text = document.get_text(root)
            if initial and initial.get(root):
                text.insert(0, initial[root])
        document.commit()
        return CollaborationDocument(
            channel_id=channel_id,
            resource_kind=resource_kind,
            resource_id=resource_id,
            snapshot=document.export(ExportMode.Snapshot()),
            version_vector=document.oplog_vv.encode(),
            root_names=list(roots),
            rich_roots=sorted(rich_roots or set()),
            initial_values=initial or {},
        )

    @staticmethod
    def document_for(
        channel_id: str,
        resource_kind: str,
        resource_id: str,
        roots: tuple[str, ...] | None = None,
        document_id: str | None = None,
        initial: dict[str, str] | None = None,
        rich_roots: set[str] | None = None,
    ) -> CollaborationDocument:
        row = CollaborationDocument.query.filter_by(channel_id=channel_id, resource_kind=resource_kind, resource_id=resource_id).first()
        if row:
            return row
        row = CollaborationStore.create_document(channel_id, resource_kind, resource_id, roots, initial, rich_roots)
        if document_id:
            row.id = document_id
        db.session.add(row)
        db.session.commit()
        return row

    def _redis_checkpoint(self, document_id: str) -> tuple[bytes, bytes, str] | None:
        values = cast(list[bytes | str | None], self.redis.mget(*(self._key(document_id, key) for key in ("snapshot", "vv", "water"))))
        if not values[0] or not values[1] or not values[2]:
            return None
        water = values[2].decode() if isinstance(values[2], bytes) else str(values[2])
        snapshot = values[0] if isinstance(values[0], bytes) else values[0].encode()
        version_vector = values[1] if isinstance(values[1], bytes) else values[1].encode()
        return snapshot, version_vector, water

    def load(self, row: CollaborationDocument, max_stream_id: str | None = None) -> Materialized:
        checkpoint = self._redis_checkpoint(row.id)
        if checkpoint is None:
            checkpoint = (bytes(row.snapshot), bytes(row.version_vector), row.stream_high_water_id)
            self.redis.mset(dict(zip((self._key(row.id, x) for x in ("snapshot", "vv", "water")), checkpoint)))
        doc = LoroDoc()
        if checkpoint[0]:
            doc.import_(checkpoint[0])
        entries = cast(
            list[tuple[bytes, dict[bytes | str, bytes | str]]],
            self.redis.xrange(self._key(row.id, "updates"), min=f"({checkpoint[2]}", max=max_stream_id or "+"),
        )
        for _, fields in entries:
            update_value = fields.get(b"update") or fields.get("update")
            update = update_value if isinstance(update_value, bytes) else update_value.encode() if update_value else None
            if update:
                doc.import_(update)
        latest = cast(
            list[tuple[bytes, dict[bytes | str, bytes | str]]],
            self.redis.xrevrange(self._key(row.id, "updates"), max=max_stream_id or "+", min=checkpoint[2], count=1),
        )
        latest_id = latest[0][0].decode() if latest else checkpoint[2]
        materialized = Materialized(doc, latest_id)
        self.cache[row.id] = materialized
        self.cache.move_to_end(row.id)
        while len(self.cache) > 32:
            self.cache.popitem(last=False)
        return materialized

    def accept(self, row: CollaborationDocument, update: bytes, update_id: str) -> tuple[str, bytes]:
        if not update or len(update) > MAX_UPDATE_BYTES:
            raise ValueError("Invalid collaboration update")
        try:
            self.redis.ping()
            materialized = self.load(row)
            materialized.document.import_(update)
            if len(materialized.document.export(ExportMode.Snapshot())) > MAX_DOCUMENT_BYTES:
                raise ValueError("Collaboration document is too large")
            marker = self._key(row.id, f"update:{update_id}")
            if not self.redis.set(marker, 1, nx=True, ex=86400):
                return materialized.stream_id, materialized.document.oplog_vv.encode()
            stream_id = self.redis.xadd(self._key(row.id, "updates"), {"update": update, "update_id": update_id})
            self.redis.incr(self._key(row.id, "dirty-generation"))
            self.redis.set(self._key(row.id, "dirty"), 1)
            return stream_id.decode() if isinstance(stream_id, bytes) else stream_id, materialized.document.oplog_vv.encode()
        except RedisError:
            self.cache.pop(row.id, None)
            raise
        except (RuntimeError, TypeError, ValueError):
            raise ValueError("Invalid collaboration update") from None

    def sync(self, row: CollaborationDocument, version_vector: bytes, update: bytes | None = None) -> bytes:
        materialized = self.load(row)
        if update:
            materialized.document.import_(update)
        try:
            caller_vv = VersionVector.decode(version_vector)
        except (RuntimeError, TypeError):
            raise ValueError("Invalid version vector") from None
        return materialized.document.export(ExportMode.Updates(caller_vv))

    def presence(self, document_id: str) -> list[dict[str, Any]]:
        entries = []
        for key in self.redis.scan_iter(match=self._key(document_id, "presence:") + "*"):
            value = self.redis.get(key)
            if value:
                entries.append(json.loads(value))
        return entries

    def set_presence(self, document_id: str, session_id: str, value: dict[str, Any]) -> None:
        self.redis.setex(self._key(document_id, f"presence:{session_id}"), PRESENCE_TTL, json.dumps(value, separators=(",", ":")))

    def delete_presence(self, document_id: str, session_id: str) -> None:
        self.redis.delete(self._key(document_id, f"presence:{session_id}"))

    def queue_operation(self, channel_id: str, operation: dict[str, Any]) -> None:
        self.redis.rpush(self._key(channel_id, "pending-operations"), json.dumps(operation, separators=(",", ":")))

    def pending_operations(self, channel_id: str) -> list[dict[str, Any]]:
        values = self.redis.lrange(self._key(channel_id, "pending-operations"), 0, -1)
        return [json.loads(value) for value in values]

    def clear_pending_operation(self, channel_id: str, operation_id: str) -> None:
        key = self._key(channel_id, "pending-operations")
        for value in self.redis.lrange(key, 0, -1):
            try:
                if json.loads(value).get("operation_id") == operation_id:
                    self.redis.lrem(key, 1, value.decode() if isinstance(value, bytes) else value)
            except (TypeError, ValueError):
                continue

    def add_conflict(self, channel_id: str, conflict: dict[str, Any]) -> None:
        self.redis.rpush(self._key(channel_id, "conflicts"), json.dumps(conflict, separators=(",", ":")))

    def conflicts(self, channel_id: str) -> list[dict[str, Any]]:
        return [json.loads(value) for value in self.redis.lrange(self._key(channel_id, "conflicts"), 0, -1)]

    def resolve_conflict(self, channel_id: str, operation_id: str) -> None:
        key = self._key(channel_id, "conflicts")
        for value in self.redis.lrange(key, 0, -1):
            try:
                if json.loads(value).get("operation_id") == operation_id:
                    self.redis.lrem(key, 1, value.decode() if isinstance(value, bytes) else value)
            except (TypeError, ValueError):
                continue

    def checkpoint(self, row: CollaborationDocument) -> bool:
        lock = self.redis.lock(self._key(row.id, "checkpoint-lock"), timeout=30, blocking_timeout=2)
        if not lock.acquire(blocking=True):
            return False
        try:
            generation = self.redis.get(self._key(row.id, "dirty-generation"))
            captured = cast(list[tuple[bytes, dict[bytes | str, bytes | str]]], self.redis.xrevrange(self._key(row.id, "updates"), count=1))
            captured_id = captured[0][0].decode() if captured else row.stream_high_water_id
            materialized = self.load(row, captured_id)
            if generation != self.redis.get(self._key(row.id, "dirty-generation")):
                materialized = self.load(row)
                captured_id = materialized.stream_id
            snapshot = materialized.document.export(ExportMode.Snapshot())
            version_vector = materialized.document.oplog_vv.encode()
            if len(snapshot) > MAX_DOCUMENT_BYTES:
                raise ValueError("Collaboration document is too large")
            row.snapshot = snapshot
            row.version_vector = version_vector
            row.stream_high_water_id = captured_id
            db.session.commit()
            self.redis.mset(
                {self._key(row.id, "snapshot"): snapshot, self._key(row.id, "vv"): version_vector, self._key(row.id, "water"): captured_id}
            )
            self.redis.xtrim(self._key(row.id, "updates"), minid=captured_id, approximate=False)
            self.redis.delete(self._key(row.id, "dirty"))
            return True
        finally:
            lock.release()

    def text_values(self, row: CollaborationDocument) -> dict[str, str]:
        document = self.load(row).document
        roots = ("title", "description", "summary", "comments") if row.resource_kind == "story" else ("title",)
        return {root: document.get_text(root).to_string() for root in roots}

    def rich_text_value(self, row: CollaborationDocument, root: str) -> tuple[str, str]:
        from core.service.collaboration_projection import project_prosemirror, project_rich_text

        document = self.load(row).document
        try:
            value = document.get_map(root).get_value()
        except (RuntimeError, TypeError):
            value = None
        if isinstance(value, dict) and value.get("type"):
            return project_prosemirror(value)
        return project_rich_text(cast(list[dict[str, Any]], document.get_text(root).get_richtext_value()))

    def synchronize_with_peer(self, row: CollaborationDocument, peer_url: str, token: str) -> bool:
        generation_key = self._key(row.id, f"federation:{peer_url}:generation")
        generation = self.redis.get(self._key(row.id, "dirty-generation")) or b"0"
        self.redis.set(generation_key, generation)
        document = self.load(row).document
        version = document.oplog_vv
        payload = {
            "version_vector": encode(version.encode()),
            "update": encode(document.export(ExportMode.Updates(VersionVector()))),
            "update_id": f"{Config.COLLABORATION_INSTANCE_URL}:{version.encode().hex()}",
        }
        # ponytail: three retries with bounded backoff; move to durable retry scheduling if federation outages persist.
        for attempt in range(3):
            try:
                response = requests.post(
                    f"{peer_url.rstrip('/')}{Config.APPLICATION_ROOT}api/peer-documents/{row.id}/sync",
                    json=payload,
                    headers={"X-Peer-Base-URL": Config.COLLABORATION_INSTANCE_URL.rstrip("/"), "X-Channel-Token": token},
                    timeout=(2, 10),
                )
                response.raise_for_status()
                missing = response.json().get("update", "")
                if missing:
                    self.accept(row, decode(missing), f"peer-response:{peer_url}:{payload['update_id']}:{attempt}")
                if generation == self.redis.get(self._key(row.id, "dirty-generation")):
                    self.redis.delete(generation_key)
                return True
            except (requests.RequestException, ValueError, KeyError, TypeError):
                if attempt < 2:
                    time.sleep(2**attempt)
        return False


def encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def decode(value: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, TypeError):
        raise ValueError("Invalid collaboration binary payload") from None


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


collaboration_store = CollaborationStore

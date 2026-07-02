from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Mapped

from core.managers.db_manager import db
from core.model.base_model import BaseModel


class CollaborationChannelRecord(BaseModel):
    __tablename__ = "collaboration_channel"

    channel_id: Mapped[str] = db.Column(db.String(64), primary_key=True)
    topic: Mapped[str] = db.Column(db.String(), nullable=False)
    status: Mapped[str] = db.Column(db.String(16), nullable=False, default="open")
    owner_base_url: Mapped[str] = db.Column(db.String(), nullable=False)
    created_at: Mapped[datetime | None] = db.Column(db.DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = db.Column(db.DateTime, nullable=True)
    state: Mapped[dict[str, Any]] = db.Column(db.JSON, nullable=False, default=dict)

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value)

    @classmethod
    def upsert_state(cls, channel_state: dict[str, Any]) -> "CollaborationChannelRecord":
        channel_id = str(channel_state.get("channel_id") or "")
        if not channel_id:
            raise ValueError("Collaboration channel state is missing channel_id")

        record = cls.get(channel_id)
        if record is None:
            record = cls(channel_id=channel_id)
            db.session.add(record)

        record.topic = str(channel_state.get("topic") or "")
        record.status = str(channel_state.get("status") or "open")
        record.owner_base_url = str(channel_state.get("owner_base_url") or "")
        record.created_at = cls._parse_datetime(channel_state.get("created_at"))
        record.updated_at = cls._parse_datetime(channel_state.get("updated_at"))
        record.state = deepcopy(channel_state)
        db.session.commit()
        return record

    @classmethod
    def get_all(cls) -> list["CollaborationChannelRecord"]:
        stmt = db.select(cls).order_by(cls.created_at.desc(), cls.channel_id.desc())
        return list(db.session.execute(stmt).scalars().all())

    def __init__(self, channel_id: str, **kwargs):
        self.channel_id = channel_id
        self.topic = kwargs.get("topic", "")
        self.status = kwargs.get("status", "open")
        self.owner_base_url = kwargs.get("owner_base_url", "")
        self.created_at = kwargs.get("created_at")
        self.updated_at = kwargs.get("updated_at")
        self.state = kwargs.get("state", {})

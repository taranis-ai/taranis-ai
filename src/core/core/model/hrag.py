"""Durable indexing state. Redis jobs and Neo4j are rebuildable projections."""

from datetime import datetime

from sqlalchemy.orm import Mapped

from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel


class HragGeneration(BaseModel):
    __tablename__ = "hrag_generation"

    id: Mapped[str] = db.Column(db.String(64), primary_key=True)
    pipeline: Mapped[str] = db.Column(db.String(16), nullable=False, index=True)
    config: Mapped[dict] = db.Column(db.JSON, nullable=False)
    active: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    cursor: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), nullable=False, default="")
    scanned: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    created: Mapped[datetime] = db.Column(db.DateTime, nullable=False, default=BaseModel.utcnow)


class HragWork(BaseModel):
    __tablename__ = "hrag_work"
    __table_args__ = (db.UniqueConstraint("generation_id", "news_item_id"),)

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    generation_id: Mapped[str] = db.Column(db.String(64), db.ForeignKey("hrag_generation.id", ondelete="CASCADE"), nullable=False, index=True)
    news_item_id: Mapped[str] = db.Column(
        db.String(UUID_STR_LENGTH), db.ForeignKey("news_item.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fingerprint: Mapped[str] = db.Column(db.String(64), nullable=False)
    status: Mapped[str] = db.Column(db.String(16), nullable=False, default="pending", index=True)
    token: Mapped[str | None] = db.Column(db.String(UUID_STR_LENGTH))
    lease_until: Mapped[datetime | None] = db.Column(db.DateTime)
    retry_after: Mapped[datetime | None] = db.Column(db.DateTime)
    attempts: Mapped[int] = db.Column(db.Integer, nullable=False, default=0)
    result: Mapped[dict | None] = db.Column(db.JSON)
    truncated: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    updated: Mapped[datetime] = db.Column(db.DateTime, nullable=False, default=BaseModel.utcnow)

    @property
    def graph_key(self) -> str:
        return f"{self.id}:{self.fingerprint}"


class HragMessage(BaseModel):
    """References only; evidence passages are reconstructed after authorization."""

    __tablename__ = "hrag_message"
    message_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("chat_message.id", ondelete="CASCADE"), primary_key=True)
    metadata_json: Mapped[dict] = db.Column(db.JSON, nullable=False)

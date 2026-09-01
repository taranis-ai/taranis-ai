from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped

from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel


class CollaborationDocument(BaseModel):
    __tablename__ = "collaboration_document"
    __table_args__ = (UniqueConstraint("channel_id", "resource_kind", "resource_id"),)

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    channel_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), nullable=False, index=True)
    resource_kind: Mapped[str] = db.Column(db.String(32), nullable=False)
    resource_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), nullable=False)
    schema_version: Mapped[int] = db.Column(db.Integer, nullable=False, default=1)
    root_names: Mapped[list[str]] = db.Column(db.JSON, nullable=False, default=list)
    rich_roots: Mapped[list[str]] = db.Column(db.JSON, nullable=False, default=list)
    initial_values: Mapped[dict[str, str]] = db.Column(db.JSON, nullable=False, default=dict)
    snapshot: Mapped[bytes] = db.Column(db.LargeBinary, nullable=False, default=b"")
    version_vector: Mapped[bytes] = db.Column(db.LargeBinary, nullable=False, default=b"\x00")
    stream_high_water_id: Mapped[str] = db.Column(db.String(64), nullable=False, default="0-0")
    created_at: Mapped[datetime] = db.Column(db.DateTime, default=BaseModel.utcnow, nullable=False)
    updated_at: Mapped[datetime] = db.Column(db.DateTime, default=BaseModel.utcnow, onupdate=BaseModel.utcnow, nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

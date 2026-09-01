from datetime import datetime

from sqlalchemy.orm import Mapped

from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel


class CollaborationChannel(BaseModel):
    __tablename__ = "collaboration_channel"

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    topic: Mapped[str] = db.Column(db.String(512), nullable=False, default="")
    owner_base_url: Mapped[str] = db.Column(db.String(2048), nullable=False)
    owner_token_hash: Mapped[str] = db.Column(db.String(128), nullable=False)
    owner_token: Mapped[str] = db.Column(db.String(256), nullable=False, default="")
    status: Mapped[str] = db.Column(db.String(16), nullable=False, default="open")
    participant_urls: Mapped[list[str]] = db.Column(db.JSON, nullable=False, default=list)
    report_member_ids: Mapped[list[str]] = db.Column(db.JSON, nullable=False, default=list)
    member_ids: Mapped[list[str]] = db.Column(db.JSON, nullable=False, default=list)
    story_snapshots: Mapped[list[dict]] = db.Column(db.JSON, nullable=False, default=list)
    report_drafts: Mapped[list[dict]] = db.Column(db.JSON, nullable=False, default=list)
    metadata_version: Mapped[int] = db.Column(db.Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = db.Column(db.DateTime, default=BaseModel.utcnow, nullable=False)
    updated_at: Mapped[datetime] = db.Column(db.DateTime, default=BaseModel.utcnow, onupdate=BaseModel.utcnow, nullable=False)

    def __init__(self, owner_base_url: str, owner_token_hash: str, owner_token: str = "", **kwargs):
        self.owner_base_url = owner_base_url
        self.owner_token_hash = owner_token_hash
        self.owner_token = owner_token
        for key, value in kwargs.items():
            if hasattr(type(self), key):
                setattr(self, key, value)

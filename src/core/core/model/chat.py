from datetime import datetime
from typing import Any

from sqlalchemy.orm import Mapped, relationship

from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel


class ChatConversation(BaseModel):
    __tablename__ = "chat_conversation"

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    user_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = db.Column(db.String(120), nullable=False)
    created: Mapped[datetime] = db.Column(db.DateTime, default=BaseModel.utcnow, nullable=False)
    updated: Mapped[datetime] = db.Column(db.DateTime, default=BaseModel.utcnow, nullable=False)
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created, ChatMessage.id",
        passive_deletes=True,
    )

    @classmethod
    def get_for_user(cls, conversation_id: str, user_id: str) -> "ChatConversation | None":
        return cls.get_first(db.select(cls).where(cls.id == conversation_id, cls.user_id == user_id))

    @classmethod
    def get_all_for_user(cls, user_id: str) -> list["ChatConversation"]:
        return list(db.session.scalars(db.select(cls).where(cls.user_id == user_id).order_by(cls.updated.desc())).all())

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "created": self.serialize_datetime(self.created),
            "updated": self.serialize_datetime(self.updated),
        }

    def to_detail_dict(self) -> dict[str, Any]:
        return {**self.to_summary_dict(), "messages": [message.to_dict() for message in self.messages]}


class ChatMessage(BaseModel):
    __tablename__ = "chat_message"

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    conversation_id: Mapped[str] = db.Column(
        db.String(UUID_STR_LENGTH), db.ForeignKey("chat_conversation.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = db.Column(db.String(16), nullable=False)
    content: Mapped[str] = db.Column(db.Text, nullable=False)
    created: Mapped[datetime] = db.Column(db.DateTime, default=BaseModel.utcnow, nullable=False)
    search_result: Mapped[dict[str, Any] | None] = db.Column(db.JSON, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "created": self.serialize_datetime(self.created),
            "search_result": self.search_result,
        }

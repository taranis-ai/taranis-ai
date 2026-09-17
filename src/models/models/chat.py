import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import ConfigDict, Field, field_validator

from models.base import TaranisBaseModel


CHAT_MESSAGE_MAX_LENGTH = 4000


def _uuid7() -> uuid.UUID:
    return vars(uuid)["uuid7"]()


class ChatSearchResult(TaranisBaseModel):
    filters: dict[str, str | list[str]]
    total_count: int = Field(ge=0)
    story_ids: list[str] = Field(default_factory=list)


class ChatMessage(TaranisBaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    created: datetime
    search_result: ChatSearchResult | None = None


class ChatConversationSummary(TaranisBaseModel):
    id: str
    title: str
    created: datetime
    updated: datetime


class ChatConversation(ChatConversationSummary):
    messages: list[ChatMessage] = Field(default_factory=list)


class ChatConversationList(TaranisBaseModel):
    items: list[ChatConversationSummary] = Field(default_factory=list)


class ChatTurnRequest(TaranisBaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=CHAT_MESSAGE_MAX_LENGTH)
    turn_id: uuid.UUID = Field(default_factory=_uuid7)

    @field_validator("content", mode="before")
    @classmethod
    def normalize_content(cls, value: Any) -> str:
        content = str(value or "").strip()
        if not content:
            raise ValueError("Message is required")
        return content


class ChatTurnResponse(TaranisBaseModel):
    conversation: ChatConversation

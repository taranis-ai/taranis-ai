import contextlib
import hashlib
import re
from datetime import datetime, timezone
from typing import Annotated, Any, Literal, Self
from urllib.parse import quote, unquote

import language_tags
from bs4 import BeautifulSoup
from pydantic import BeforeValidator, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from models.base import TaranisBaseModel
from models.types import CONNECTOR_TYPES


NEWS_ITEM_IMPORT_FIELDS = frozenset(
    {
        "id",
        "title",
        "source",
        "content",
        "osint_source_id",
        "review",
        "author",
        "link",
        "language",
        "hash",
        "attributes",
        "tags",
        "last_change",
        "published",
        "collected",
        "story_id",
    }
)

STORY_IMPORT_FIELDS = frozenset(
    {
        "id",
        "title",
        "description",
        "created",
        "likes",
        "dislikes",
        "relevance",
        "relevance_override",
        "read",
        "important",
        "summary",
        "comments",
        "revision",
        "attributes",
        "news_items",
        "last_change",
    }
)


def _dump_core_fields(model: TaranisBaseModel, allowed_fields: frozenset[str]) -> dict[str, Any]:
    data = model.model_dump(mode="json")
    return {key: value for key, value in data.items() if key in allowed_fields}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_datetime(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        with contextlib.suppress(ValueError):
            value = datetime.fromisoformat(value)
        if isinstance(value, str):
            return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def validate_bcp47(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("BCP 47 language tag must be a string")
    normalized = value.strip().lower()
    if not normalized:
        return None
    if not language_tags.tags.check(normalized):
        raise ValueError(f"Invalid BCP 47 language tag: {normalized}")
    return normalized


BCP47 = Annotated[str | None, BeforeValidator(validate_bcp47)]


class SimpleWebCollectorFetchParameters(TaranisBaseModel):
    model_config = ConfigDict(extra="allow")

    WEB_URL: str = Field(min_length=1)
    ADDITIONAL_HEADERS: str | None = None


class NewsItem(TaranisBaseModel):
    _core_endpoint = "/assess/news-items"
    _model_name = "news_item"
    _pretty_name = "News Item"

    osint_source_id: str
    id: str | None = None
    hash: str | None = None
    title: str | None = None
    author: str | None = None
    review: str | None = None
    content: str | None = None
    link: str | None = None
    source: str | None = None
    published: datetime | None = None
    collected: datetime | None = None
    updated: datetime | None = None
    attributes: list[str | dict[str, Any]] | None = None
    tags: list[dict[str, Any]] | dict[str, Any] | None = None
    story_id: str | None = None
    language: BCP47 = None
    last_change: str | None = None
    osint_source_key: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_model_input(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        normalized.pop("updated", None)
        normalized.pop("hash", None)
        if normalized.get("language") in ("", None):
            normalized.pop("language", None)
        return normalized

    @classmethod
    def from_input(cls, data: Any) -> Self:
        """Untrusted input: run validators + sanitizers."""
        return cls.model_validate(data)

    @classmethod
    def from_db(cls, data: dict[str, Any]) -> Self:
        """Trusted DB row: skip *all* validators/sanitizers."""
        return cls.model_construct(**data)

    @classmethod
    def normalize_datetime(cls, date: str | datetime | None, default_to_now: bool = False) -> datetime | None:
        return _normalize_datetime(date) or (_utcnow() if default_to_now else None)

    @model_validator(mode="after")
    def check_required_fields(self) -> Self:
        if not self.title and not self.content:
            raise ValueError("Either title or content must be provided.")
        return self

    @field_validator("title", "content", mode="before")
    @classmethod
    def sanitize_html(cls, value: str, info: ValidationInfo) -> str:
        if not value:
            return ""
        html = re.sub(r"(?i)(&nbsp;|\xa0)", " ", value)
        return BeautifulSoup(html, "lxml").text

    @field_validator("link", mode="before")
    @classmethod
    def sanitize_url(cls, url: str, info: ValidationInfo) -> str:
        return quote(unquote(url or ""), safe="/:@?&=+$,;")

    @model_validator(mode="after")
    def ensure_hash(self) -> Self:
        if not self.hash:
            title = self.title or ""
            link = self.link or ""
            self.hash = hashlib.sha256((title + link).encode()).hexdigest()
        return self

    @field_validator("published", "collected", mode="before")
    @classmethod
    def sanitize_date(cls, date: str | None | datetime) -> datetime:
        return cls.normalize_datetime(date, default_to_now=True) or _utcnow()

    def to_core_dict(self) -> dict[str, Any]:
        return _dump_core_fields(self, NEWS_ITEM_IMPORT_FIELDS)


class StoryTag(TaranisBaseModel):
    name: str
    size: int
    type: str | None = None


class Story(TaranisBaseModel):
    _core_endpoint = "/assess/stories"
    _model_name = "story"
    _pretty_name = "Story"
    _cache_timeout = 30

    id: str | None = None
    title: str | None = None
    description: str | None = None
    created: datetime | None = None
    updated: datetime | None = None
    last_change: str | None = None
    news_items: list[NewsItem] | None = None
    links: list[str] | None = None
    important: bool | None = None
    read: bool | None = None
    likes: int | None = None
    dislikes: int | None = None
    user_vote: Literal["like", "dislike", "", None] = None
    summary: str | None = None
    relevance: int | None = None
    relevance_override: int | None = None
    comments: str | None = None
    in_reports_count: int | None = None
    tags: list[dict[str, Any]] | None = None
    attributes: list[dict[str, Any]] | None = None

    @classmethod
    def normalize_datetime(cls, date: str | datetime | None) -> datetime | None:
        return _normalize_datetime(date)

    @model_validator(mode="before")
    @classmethod
    def normalize_story_payload(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        tags = normalized.get("tags")
        if isinstance(tags, dict):
            normalized["tags"] = list(tags.values())
        return normalized

    @field_validator("created", "updated", mode="before")
    @classmethod
    def sanitize_story_dates(cls, date: str | None | datetime) -> datetime | None:
        return cls.normalize_datetime(date)

    def to_core_dict(self) -> dict[str, Any]:
        data = _dump_core_fields(self, STORY_IMPORT_FIELDS)
        if self.news_items is not None:
            data["news_items"] = [news_item.to_core_dict() if isinstance(news_item, NewsItem) else news_item for news_item in self.news_items]
        return data


class AssessSource(TaranisBaseModel):
    id: str | None = None
    icon: str | None = None
    name: str
    type: str | None = None


class Connector(TaranisBaseModel):
    _core_endpoint = "/assess/connectors"
    _model_name = "connector"
    _pretty_name = "Connector"

    id: str | None = None
    name: str
    description: str = ""
    type: CONNECTOR_TYPES | None = None


class FilterLists(TaranisBaseModel):
    _core_endpoint = "/assess/filterlists"
    _model_name = "filter_lists"
    _pretty_name = "Filter Lists"

    tags: list[str] = Field(default_factory=list)
    sources: list[AssessSource] = Field(default_factory=list)
    groups: list[dict[str, str | None]] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)


class StoryBookmarkBase(TaranisBaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: Any) -> str:
        name = str(value or "").strip()
        if not name:
            raise ValueError("Bookmark collection name is required")
        return name


class StoryBookmarkCreatePayload(StoryBookmarkBase):
    pass


class StoryBookmarkUpdatePayload(StoryBookmarkBase):
    pass


class StoryBookmarkStoryPayload(TaranisBaseModel):
    story_ids: list[str] = Field(min_length=1)


class StoryBookmarkOrderPayload(TaranisBaseModel):
    bookmark_ids: list[str] = Field(min_length=1)


class StoryBookmark(StoryBookmarkBase):
    _core_endpoint = "/assess/bookmarks"
    _model_name = "story_bookmark"
    _pretty_name = "Story Bookmark Collection"
    _cache_timeout = 30

    id: str | None = None
    position: int = 0
    created: datetime | None = None
    updated: datetime | None = None
    story_count: int = 0
    story_ids: list[str] = Field(default_factory=list)
    stories: list[Story] = Field(default_factory=list)


class StoryUpdatePayload(TaranisBaseModel):
    model_config = ConfigDict(extra="ignore")

    vote: Literal["like", "dislike", ""] | None = None
    important: bool | None = None
    read: bool | None = None
    title: str | None = None
    description: str | None = None
    comments: str | None = None
    summary: str | None = None
    attributes: list[dict[str, Any]] | None = None


class BulkAction(TaranisBaseModel):
    story_ids: list[str] = []
    payload: StoryUpdatePayload | None = None

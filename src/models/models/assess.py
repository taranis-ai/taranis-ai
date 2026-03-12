import contextlib
import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Literal, Self
from urllib.parse import quote

from bs4 import BeautifulSoup
from langcodes import Language
from langcodes.tag_parser import LanguageTagError
from pydantic import ValidationInfo, field_validator, model_validator

from models.base import TaranisBaseModel


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


class NewsItem(TaranisBaseModel):
    _core_endpoint = "/assess/news-items"

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
    story_id: str | None = None
    language: str | None = None
    last_change: str | None = None

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

    @field_validator("language", mode="before")
    @classmethod
    def normalize_language_code(cls, v: str, info: ValidationInfo) -> str:
        if v:
            try:
                return Language.get(v).language or ""
            except (LanguageTagError, ValueError, TypeError):
                return ""
        return ""

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
        html = re.sub(r"(?i)(&nbsp;|\xa0)", " ", value, re.DOTALL)
        return BeautifulSoup(html, "lxml").text

    @field_validator("link", mode="before")
    @classmethod
    def sanitize_url(cls, url: str, info: ValidationInfo) -> str:
        return quote(url or "", safe="/:@?&=+$,;")

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
        return cls.normalize_datetime(date, default_to_now=True)


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
    comments: str | None = None
    in_reports_count: int | None = None
    tags: list[dict[str, Any]] | None = None
    attributes: list[dict[str, Any]] | None = None

    @classmethod
    def normalize_datetime(cls, date: str | datetime | None) -> datetime | None:
        return _normalize_datetime(date)

    @field_validator("created", "updated", mode="before")
    @classmethod
    def sanitize_story_dates(cls, date: str | None | datetime) -> datetime | None:
        return cls.normalize_datetime(date)


class AssessSource(TaranisBaseModel):
    id: str | None = None
    icon: str | None = None
    name: str
    type: str | None = None


class FilterLists(TaranisBaseModel):
    _core_endpoint = "/assess/filterlists"
    _model_name = "filter_lists"
    _pretty_name = "Filter Lists"

    tags: list[str] = []
    sources: list[AssessSource] = []
    groups: list[dict[str, Any]] = []


class StoryUpdatePayload(TaranisBaseModel):
    vote: Literal["like", "dislike", ""] | None = None
    important: bool | None = None
    read: bool | None = None
    title: str | None = None
    description: str | None = None
    comments: str | None = None
    summary: str | None = None
    tags: list[dict[str, Any]] | None = None
    attributes: list[dict[str, Any]] | None = None


class BulkAction(TaranisBaseModel):
    story_ids: list[str] = []
    payload: StoryUpdatePayload | None = None

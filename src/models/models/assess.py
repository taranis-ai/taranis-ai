from datetime import datetime
from pydantic import field_validator, model_validator, field_serializer
import langcodes
from typing import Literal
from functools import cached_property

from models.base import TaranisBaseModel


class NewsItem(TaranisBaseModel):
    _core_endpoint = "/assess/newsitems"

    osint_source_id: str
    hash: str = ""
    author: str = ""
    title: str = ""
    review: str | None = None
    content: str = ""
    web_url: str = ""
    source: str = ""
    published_date: datetime | None = None
    collected_date: datetime | None = None
    attributes: list[str] | None = None
    language: str | None = None

    @field_validator("language", mode="before")
    def normalize_language_code(cls, v):
        if not v:
            return None
        try:
            lang = langcodes.find(v)
            return lang.language
        except LookupError:
            return None

    @model_validator(mode="after")
    def set_default_dates(self):
        now = datetime.now()
        if not self.collected_date:
            self.collected_date = now
        if not self.published_date:
            self.published_date = self.collected_date
        return self

    @field_serializer("published_date", "collected_date", when_used="always")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class StoryTag(TaranisBaseModel):
    name: str
    size: int
    type: str | None = None


class Story(TaranisBaseModel):
    _core_endpoint = "/assess/stories"
    _model_name = "story"
    _pretty_name = "Story"

    id: str | None = None
    title: str | None = None
    description: str | None = None
    created: datetime | None = None
    updated: datetime | None = None
    last_change: str | None = None
    news_items: list[NewsItem] = []
    links: list[str] = []
    important: bool = False
    read: bool = False
    likes: int = 0
    dislikes: int = 0
    user_vote: Literal["like", "dislike", ""] = ""
    summary: str | None = None
    relevance: int = 0
    comments: str | None = None
    in_reports_count: int = 0
    tags: list[dict] = []
    attributes: list[dict] = []

    @cached_property
    def search_field(self) -> str:
        search = ""
        search += f"{self.title.lower() if self.title else ''} {self.description.lower() if self.description else ''} "
        if self.news_items:
            search += " ".join([item.title.lower() for item in self.news_items if item.title])
            search += " ".join([item.content.lower() for item in self.news_items if item.content])
            search += " ".join([item.source.lower() for item in self.news_items if item.source])
        return search


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
    groups: list[dict] = []

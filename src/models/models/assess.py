from datetime import datetime
from pydantic import field_validator, model_validator, field_serializer
import langcodes

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

"""Shared inputs for the social monitor."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


Key = Annotated[str, Field(min_length=1, max_length=500)]
Platform = Literal["mastodon", "reddit"]


class CollectedImage(BaseModel):
    key: Key
    alt: str = Field("", max_length=8192)
    data: str | None = Field(None, max_length=16 * 1024 * 1024)


class Contribution(BaseModel):
    key: Key
    thread: Key
    parent: str = Field("", max_length=500)
    author: str = Field("", max_length=500)
    boosted_by: str = Field("", max_length=500)
    title: str = Field("", max_length=2000)
    body: str = Field("", max_length=200000)
    url: HttpUrl
    published: datetime
    warning: str = Field("", max_length=2000)
    images: list[CollectedImage] = Field(default_factory=list, max_length=20)


class BeatFilters(BaseModel):
    sources: list[str] = Field(default_factory=list, max_length=200)
    platform: Platform | None = None
    search: str = Field("", max_length=300)
    images: bool = False


class SaveBeat(BeatFilters):
    name: str = Field(min_length=1, max_length=100, pattern=r"\S")


class AttachPosts(BaseModel):
    posts: list[str] = Field(min_length=1, max_length=100)
    title: str = Field("", max_length=500)
    story_id: str = Field("", max_length=36)

    @model_validator(mode="after")
    def destination(self):
        if bool(self.story_id) == bool(self.title.strip()):
            raise ValueError("Choose an existing Story or enter a new Story title")
        return self


class ReportFigure(BaseModel):
    image_id: str
    caption: str = Field("", max_length=4000)
    alt: str = Field("", max_length=2000)


class FigureSelection(BaseModel):
    figures: list[ReportFigure] = Field(max_length=50)

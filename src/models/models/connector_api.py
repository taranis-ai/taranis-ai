"""Connector conflict review operations."""

from pydantic import BaseModel, Field, TypeAdapter

from models import dashboard
from models.api import ItemsResponse, MessageResponse, OperationContract, json_response
from models.content_api import ContentError, ManualNewsInput, MispError, MispResult, StoryAdded, StoryInput


class StoryConflicts(BaseModel):
    conflicts: list[dashboard.StoryConflict]


class Resolution(BaseModel):
    resolution: StoryInput = Field(default_factory=StoryInput)
    incoming_story_original: StoryInput = Field(default_factory=StoryInput)


class AddNews(BaseModel):
    incoming_story_id: str | None = None
    story_id: str | None = None
    news_items: list[ManualNewsInput] = Field(default_factory=list)


class UngroupIncoming(BaseModel):
    existing_story_ids: list[str]
    incoming_news_item_ids: list[str]
    incoming_story: StoryInput
    remaining_stories: list[StoryInput] = Field(default_factory=list)


class AddedNews(MessageResponse):
    added_ids: list[str]
    errors: list[ContentError] = Field(default_factory=list)


class NewsTitle(BaseModel):
    id: str
    title: str | None


class StorySummary(BaseModel):
    id: str
    title: str | None
    is_misp_story: bool
    news_item_count: int
    relevance: int
    news_item_data: list[NewsTitle]


OPERATIONS = (
    *(
        OperationContract("GET", path, {200: json_response(StoryConflicts | dashboard.StoryConflict)})
        for path in ("/connectors/conflicts/stories", "/connectors/conflicts/stories/{story_id}")
    ),
    *(
        OperationContract(
            "PUT",
            path,
            {
                200: json_response(MispResult | MispError),
                **{status: json_response(ContentError | MispError) for status in (400, 404, 409, 500)},
            },
            body=TypeAdapter(Resolution),
        )
        for path in ("/connectors/conflicts/stories", "/connectors/conflicts/stories/{story_id}")
    ),
    OperationContract("GET", "/connectors/conflicts/news-items", {200: json_response(ItemsResponse[dashboard.NewsItemConflict])}),
    OperationContract(
        "POST", "/connectors/conflicts/news-items", {200: json_response(AddedNews), 207: json_response(AddedNews)}, body=TypeAdapter(AddNews)
    ),
    OperationContract(
        "PUT",
        "/connectors/conflicts/news-items",
        {200: json_response(StoryAdded), **{status: json_response(ContentError) for status in (400, 409, 500)}},
        body=TypeAdapter(UngroupIncoming),
    ),
    OperationContract("GET", "/connectors/story-summary/{story_id}", {200: json_response(StorySummary)}),
    OperationContract("POST", "/connectors/conflicts/clear", {200: json_response(MessageResponse)}),
)

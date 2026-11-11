"""Structured frontend endpoints; ordinary HTML page rendering is outside HTTP API coverage."""

from dataclasses import replace

from pydantic import BaseModel, Field, TypeAdapter

from models.api import OperationContract, download_response, json_response
from models.connector_api import AddNews, UngroupIncoming
from models.content_api import StoryInput
from models.user import UserProfileResponse


class ConflictForm(BaseModel):
    resolved_story: StoryInput
    incoming_original: StoryInput = Field(default_factory=StoryInput)


class UniqueNews(AddNews):
    existing_story_news_item_ids: list[str] = Field(default_factory=list)
    remaining_stories: list[StoryInput] = Field(default_factory=list)


OPERATIONS = (
    OperationContract("GET", "/list_user_cache", {200: json_response(list[UserProfileResponse])}),
    OperationContract("POST", "/conflicts/story/{story_id}/resolve", {200: download_response("text/html")}, body=TypeAdapter(ConflictForm)),
    OperationContract("POST", "/conflicts/news-items", {200: download_response("text/html")}, body=TypeAdapter(UniqueNews)),
    OperationContract("PUT", "/conflicts/news-items", {200: download_response("text/html")}, body=TypeAdapter(UngroupIncoming)),
)


# These endpoints render HTML notifications and login redirects on failures.
OPERATIONS = tuple(
    replace(
        operation,
        responses={
            **{status: download_response() for status in (302, 303, 400, 401, 403, 404, 409, 422, 500, 502, 503)},
            **operation.responses,
        },
    )
    for operation in OPERATIONS
)

"""Bot service boundary contracts."""

from pydantic import TypeAdapter

from models import admin, assess
from models.api import ErrorResponse, IdMessageResponse, ItemsResponse, MessageResponse, OperationContract, json_response
from models.config_api import BotQuery
from models.content_api import (
    Attribute,
    AttributeEnvelope,
    AttributePayload,
    LanguageUpdate,
    NewsIds,
    NewsItemResponse,
    NewsUpdated,
    StoryGroups,
    StoryIds,
    StoryResponse,
    StoryUpdated,
)


OPERATIONS = (
    *(
        OperationContract("GET", path, {200: json_response(ItemsResponse[admin.Bot] if path == "/bots" else admin.Bot)}, query=BotQuery)
        for path in ("/bots", "/bots/{bot_id}")
    ),
    *(
        OperationContract(
            "PUT",
            path,
            {200: json_response(IdMessageResponse), 404: json_response(MessageResponse | ErrorResponse)},
            body=TypeAdapter(admin.BotUpdate),
        )
        for path in ("/bots", "/bots/{bot_id}")
    ),
    OperationContract("GET", "/bots/news-item/{news_item_id}", {200: json_response(NewsItemResponse)}),
    OperationContract(
        "PUT",
        "/bots/news-item/{news_item_id}",
        {200: json_response(NewsUpdated | MessageResponse)},
        body=TypeAdapter(LanguageUpdate),
        validation_error_message="Invalid news item data: Invalid BCP 47 language tag",
    ),
    OperationContract(
        "PUT",
        "/bots/news-item/{news_item_id}/attributes",
        {200: json_response(MessageResponse)},
        body=TypeAdapter(AttributeEnvelope | AttributePayload),
    ),
    OperationContract("GET", "/bots/story/{story_id}", {200: json_response(StoryResponse)}),
    OperationContract("PUT", "/bots/story/{story_id}", {200: json_response(StoryUpdated)}, body=TypeAdapter(assess.StoryUpdatePayload)),
    OperationContract(
        "GET", "/bots/story/{story_id}/attributes", {200: json_response(list[Attribute]), 404: json_response(MessageResponse | ErrorResponse)}
    ),
    OperationContract(
        "PATCH",
        "/bots/story/{story_id}/attributes",
        {200: json_response(MessageResponse)},
        body=TypeAdapter(AttributeEnvelope | AttributePayload),
    ),
    OperationContract("PUT", "/bots/stories/group", {200: json_response(MessageResponse)}, body=TypeAdapter(list[str] | StoryIds)),
    OperationContract(
        "PUT", "/bots/stories/group-multiple", {200: json_response(MessageResponse)}, body=TypeAdapter(list[list[str]] | StoryGroups)
    ),
    OperationContract("PUT", "/bots/stories/ungroup", {200: json_response(MessageResponse)}, body=TypeAdapter(list[str] | NewsIds)),
)

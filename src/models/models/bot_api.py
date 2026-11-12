"""Bot service boundary contracts."""

from models import admin, assess
from models.api import ApiEndpointModels, ErrorResponse, IdMessageResponse, ItemsResponse, MessageResponse, json_response
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
        ApiEndpointModels("GET", path, {200: json_response(ItemsResponse[admin.Bot] if path == "/bots" else admin.Bot)}, query=BotQuery)
        for path in ("/bots", "/bots/{bot_id}")
    ),
    *(
        ApiEndpointModels(
            "PUT",
            path,
            {200: json_response(IdMessageResponse), 404: json_response(MessageResponse | ErrorResponse)},
            body=admin.BotUpdate,
        )
        for path in ("/bots", "/bots/{bot_id}")
    ),
    ApiEndpointModels("GET", "/bots/news-item/{news_item_id}", {200: json_response(NewsItemResponse)}),
    ApiEndpointModels(
        "PUT",
        "/bots/news-item/{news_item_id}",
        {200: json_response(NewsUpdated | MessageResponse)},
        body=LanguageUpdate,
    ),
    ApiEndpointModels(
        "PUT",
        "/bots/news-item/{news_item_id}/attributes",
        {200: json_response(MessageResponse)},
        body=AttributeEnvelope | AttributePayload,
    ),
    ApiEndpointModels("GET", "/bots/story/{story_id}", {200: json_response(StoryResponse)}),
    ApiEndpointModels("PUT", "/bots/story/{story_id}", {200: json_response(StoryUpdated)}, body=assess.StoryUpdatePayload),
    ApiEndpointModels(
        "GET", "/bots/story/{story_id}/attributes", {200: json_response(list[Attribute]), 404: json_response(MessageResponse | ErrorResponse)}
    ),
    ApiEndpointModels(
        "PATCH",
        "/bots/story/{story_id}/attributes",
        {200: json_response(MessageResponse)},
        body=AttributeEnvelope | AttributePayload,
    ),
    ApiEndpointModels("PUT", "/bots/stories/group", {200: json_response(MessageResponse)}, body=list[str] | StoryIds),
    ApiEndpointModels("PUT", "/bots/stories/group-multiple", {200: json_response(MessageResponse)}, body=list[list[str]] | StoryGroups),
    ApiEndpointModels("PUT", "/bots/stories/ungroup", {200: json_response(MessageResponse)}, body=list[str] | NewsIds),
)

"""Assessment HTTP contracts, including supported import and update variants."""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field, HttpUrl, JsonValue, TypeAdapter, field_validator

from models import assess
from models.api import ApiEndpointModels, IdMessageResponse, ItemsResponse, MessageResponse, PageResponse, download_response, json_response
from models.base import TaranisBaseModel
from models.config_api import ListQuery, QueueNotice
from models.content_api import (
    AttributeEnvelope,
    AttributePayload,
    BookmarkAdded,
    BookmarkRemoved,
    BookmarkSaved,
    BookmarkWritten,
    BotAction,
    BulkResponse,
    BulkWrite,
    ContentError,
    ContentQuery,
    CountResponse,
    ImportedNews,
    ImportedStories,
    ManualNewsInput,
    NewsDeleted,
    NewsItemResponse,
    NewsUpdate,
    NewsUpdated,
    ReviewActionResponse,
    Revision,
    RevisionData,
    StoryAdded,
    StoryFilters,
    StoryIds,
    StoryPage,
    StoryResponse,
    StoryRevisionPath,
    StoryUpdated,
    TagPayload,
    Ungrouped,
    validate_import,
)
from models.cti import CTIResponse


class Reference(TaranisBaseModel):
    id: str
    key: str | None = None
    name: str
    rank: int | None = None
    type: str | None = None
    icon: str | None = None


class TagSuggestion(BaseModel):
    name: str
    story_count: int


class WebParameters(TaranisBaseModel):
    WEB_URL: str

    @field_validator("WEB_URL")
    @classmethod
    def validate_url(cls, value):
        TypeAdapter(HttpUrl).validate_python(value)
        return value


class FetchInput(TaranisBaseModel):
    parameters: WebParameters


class ConnectorReference(TaranisBaseModel):
    id: str
    name: str
    description: str | None = None
    type: str | None = None


class ShareInput(BaseModel):
    story_ids: list[str] = Field(default_factory=list)


CONTENT_ERRORS = {status: json_response(ContentError) for status in (400, 404, 409, 500)}
MULTI = ("source", "group", "tags", "language", "story_ids")
OPERATIONS = (
    *(
        ApiEndpointModels("GET", f"/assess/{path}", {200: json_response(ItemsResponse[Reference])})
        for path in ("osint-source-group-list", "osint-sources-list")
    ),
    ApiEndpointModels("GET", "/assess/taglist", {200: json_response(list[TagSuggestion])}, query=ListQuery),
    ApiEndpointModels("GET", "/assess/filter-lists", {200: json_response(assess.FilterLists)}),
    ApiEndpointModels("GET", "/assess/news-items", {200: json_response(ItemsResponse[NewsItemResponse])}, query=ContentQuery),
    ApiEndpointModels("POST", "/assess/news-items", {200: json_response(StoryAdded), **CONTENT_ERRORS}, body=ManualNewsInput),
    ApiEndpointModels(
        "POST",
        "/assess/news-items/fetch",
        {200: json_response(QueueNotice)},
        body=FetchInput,
    ),
    ApiEndpointModels("GET", "/assess/news-items/{item_id}", {200: json_response(NewsItemResponse)}),
    *(
        ApiEndpointModels(method, "/assess/news-items/{item_id}", {200: json_response(NewsUpdated)}, body=NewsUpdate)
        for method in ("PUT", "PATCH")
    ),
    ApiEndpointModels("DELETE", "/assess/news-items/{item_id}", {200: json_response(NewsDeleted)}),
    ApiEndpointModels("GET", "/assess/news-items/{item_id}/cti", {200: json_response(CTIResponse)}),
    ApiEndpointModels(
        "PUT",
        "/assess/news-items/{news_item_id}/attributes",
        {200: json_response(MessageResponse)},
        body=AttributeEnvelope | AttributePayload,
    ),
    ApiEndpointModels("PUT", "/assess/news-items/{news_item_id}/tags", {200: json_response(MessageResponse)}, body=TagPayload),
    *(
        ApiEndpointModels("GET", path, {200: json_response(StoryPage)}, query=StoryFilters, repeated_query=MULTI)
        for path in ("/assess/stories", "/assess/stories/bulk_action")
    ),
    *(
        ApiEndpointModels(
            "POST",
            path,
            {200: json_response(BulkResponse)},
            body=BulkWrite,
        )
        for path in ("/assess/stories", "/assess/stories/bulk_action")
    ),
    ApiEndpointModels(
        "GET", "/assess/stories/export", {200: download_response("application/json")}, query=StoryIds, repeated_query=("story_ids",)
    ),
    ApiEndpointModels("GET", "/assess/analyst-review/snapshot", {200: json_response(StoryIds)}),
    ApiEndpointModels(
        "POST",
        "/assess/analyst-review/actions",
        {200: json_response(ReviewActionResponse)},
        body=assess.AnalystReviewActionPayload,
    ),
    *(
        ApiEndpointModels("GET", path, {200: json_response(StoryResponse)})
        for path in ("/assess/stories/{story_id}", "/assess/story/{story_id}")
    ),
    *(
        ApiEndpointModels(method, path, {200: json_response(StoryUpdated)}, body=assess.StoryUpdatePayload)
        for path in ("/assess/stories/{story_id}", "/assess/story/{story_id}")
        for method in ("PUT", "PATCH")
    ),
    *(
        ApiEndpointModels("DELETE", path, {200: json_response(MessageResponse)})
        for path in ("/assess/stories/{story_id}", "/assess/story/{story_id}")
    ),
    ApiEndpointModels("GET", "/assess/stories/{story_id}/cti", {200: json_response(CTIResponse)}),
    ApiEndpointModels(
        "PUT",
        "/assess/stories/{story_id}/news-item-order",
        {200: json_response(MessageResponse)},
        body=assess.StoryNewsItemOrderPayload,
    ),
    *(
        ApiEndpointModels(method, path, {200: json_response(MessageResponse | IdMessageResponse | Ungrouped)}, body=list[str])
        for path, methods in (
            ("/assess/stories/group", ("PUT", "POST")),
            ("/assess/stories/ungroup", ("PUT",)),
            ("/assess/news-items/ungroup", ("PUT",)),
        )
        for method in methods
    ),
    ApiEndpointModels("POST", "/assess/stories/botactions", {200: json_response(QueueNotice)}, body=BotAction | None),
    *(
        ApiEndpointModels("GET", path, {200: json_response(ItemsResponse[ConnectorReference])}, query=ListQuery)
        for path in ("/assess/connectors", "/assess/story/{connector_id}/share")
    ),
    *(
        ApiEndpointModels("POST", path, {200: json_response(QueueNotice)}, body=ShareInput)
        for path in ("/assess/connectors", "/assess/story/{connector_id}/share")
    ),
    ApiEndpointModels("GET", "/assess/connectors/proposals", {200: json_response(CountResponse)}),
    ApiEndpointModels("GET", "/assess/stories/{story_id}/revisions", {200: json_response(PageResponse[Revision])}),
    ApiEndpointModels(
        "GET", "/assess/stories/{story_id}/revisions/{revision_number}", {200: json_response(RevisionData)}, parameters=StoryRevisionPath
    ),
    ApiEndpointModels(
        "POST",
        "/assess/import",
        {200: json_response(ImportedStories | ImportedNews)},
        body=Annotated[JsonValue, BeforeValidator(validate_import)],
    ),
    ApiEndpointModels("GET", "/assess/bookmarks", {200: json_response(PageResponse[assess.StoryBookmark])}, query=ListQuery),
    ApiEndpointModels("POST", "/assess/bookmarks", {201: json_response(BookmarkWritten)}, body=assess.StoryBookmarkCreatePayload),
    ApiEndpointModels("GET", "/assess/bookmarks/{bookmark_id}", {200: json_response(assess.StoryBookmark)}),
    ApiEndpointModels(
        "PATCH", "/assess/bookmarks/{bookmark_id}", {200: json_response(BookmarkWritten)}, body=assess.StoryBookmarkUpdatePayload
    ),
    ApiEndpointModels("DELETE", "/assess/bookmarks/{bookmark_id}", {200: json_response(MessageResponse)}),
    ApiEndpointModels("PATCH", "/assess/bookmarks/order", {200: json_response(MessageResponse)}, body=assess.StoryBookmarkOrderPayload),
    ApiEndpointModels("POST", "/assess/bookmarks/quick-save", {200: json_response(BookmarkSaved)}, body=assess.StoryBookmarkStoryPayload),
    ApiEndpointModels(
        "POST",
        "/assess/bookmarks/memberships",
        {200: json_response(MessageResponse)},
        body=assess.StoryBookmarkMembershipPayload,
    ),
    ApiEndpointModels(
        "POST",
        "/assess/bookmarks/{bookmark_id}/stories",
        {200: json_response(BookmarkAdded)},
        body=assess.StoryBookmarkStoryPayload,
    ),
    ApiEndpointModels(
        "POST",
        "/assess/bookmarks/{bookmark_id}/stories/remove",
        {200: json_response(BookmarkRemoved)},
        body=assess.StoryBookmarkStoryPayload,
    ),
)

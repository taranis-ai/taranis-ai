"""Assessment HTTP contracts, including supported import and update variants."""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field, HttpUrl, JsonValue, TypeAdapter, field_validator

from models import assess
from models.api import IdMessageResponse, ItemsResponse, MessageResponse, OperationContract, PageResponse, download_response, json_response
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
        OperationContract("GET", f"/assess/{path}", {200: json_response(ItemsResponse[Reference])})
        for path in ("osint-source-group-list", "osint-sources-list")
    ),
    OperationContract("GET", "/assess/taglist", {200: json_response(list[TagSuggestion])}, query=ListQuery),
    OperationContract("GET", "/assess/filter-lists", {200: json_response(assess.FilterLists)}),
    OperationContract("GET", "/assess/news-items", {200: json_response(ItemsResponse[NewsItemResponse])}, query=ContentQuery),
    OperationContract("POST", "/assess/news-items", {200: json_response(StoryAdded), **CONTENT_ERRORS}, body=ManualNewsInput),
    OperationContract(
        "POST",
        "/assess/news-items/fetch",
        {200: json_response(QueueNotice)},
        body=FetchInput,
    ),
    OperationContract("GET", "/assess/news-items/{item_id}", {200: json_response(NewsItemResponse)}),
    *(
        OperationContract(method, "/assess/news-items/{item_id}", {200: json_response(NewsUpdated)}, body=NewsUpdate)
        for method in ("PUT", "PATCH")
    ),
    OperationContract("DELETE", "/assess/news-items/{item_id}", {200: json_response(NewsDeleted)}),
    OperationContract("GET", "/assess/news-items/{item_id}/cti", {200: json_response(CTIResponse)}),
    OperationContract(
        "PUT",
        "/assess/news-items/{news_item_id}/attributes",
        {200: json_response(MessageResponse)},
        body=AttributeEnvelope | AttributePayload,
    ),
    OperationContract("PUT", "/assess/news-items/{news_item_id}/tags", {200: json_response(MessageResponse)}, body=TagPayload),
    *(
        OperationContract("GET", path, {200: json_response(StoryPage)}, query=StoryFilters, repeated_query=MULTI)
        for path in ("/assess/stories", "/assess/stories/bulk_action")
    ),
    *(
        OperationContract(
            "POST",
            path,
            {200: json_response(BulkResponse)},
            body=BulkWrite,
        )
        for path in ("/assess/stories", "/assess/stories/bulk_action")
    ),
    OperationContract(
        "GET", "/assess/stories/export", {200: download_response("application/json")}, query=StoryIds, repeated_query=("story_ids",)
    ),
    OperationContract("GET", "/assess/analyst-review/snapshot", {200: json_response(StoryIds)}),
    OperationContract(
        "POST",
        "/assess/analyst-review/actions",
        {200: json_response(ReviewActionResponse)},
        body=assess.AnalystReviewActionPayload,
    ),
    *(
        OperationContract("GET", path, {200: json_response(StoryResponse)})
        for path in ("/assess/stories/{story_id}", "/assess/story/{story_id}")
    ),
    *(
        OperationContract(method, path, {200: json_response(StoryUpdated)}, body=assess.StoryUpdatePayload)
        for path in ("/assess/stories/{story_id}", "/assess/story/{story_id}")
        for method in ("PUT", "PATCH")
    ),
    *(
        OperationContract("DELETE", path, {200: json_response(MessageResponse)})
        for path in ("/assess/stories/{story_id}", "/assess/story/{story_id}")
    ),
    OperationContract("GET", "/assess/stories/{story_id}/cti", {200: json_response(CTIResponse)}),
    OperationContract(
        "PUT",
        "/assess/stories/{story_id}/news-item-order",
        {200: json_response(MessageResponse)},
        body=assess.StoryNewsItemOrderPayload,
    ),
    *(
        OperationContract(method, path, {200: json_response(MessageResponse | IdMessageResponse | Ungrouped)}, body=list[str])
        for path, methods in (
            ("/assess/stories/group", ("PUT", "POST")),
            ("/assess/stories/ungroup", ("PUT",)),
            ("/assess/news-items/ungroup", ("PUT",)),
        )
        for method in methods
    ),
    OperationContract("POST", "/assess/stories/botactions", {200: json_response(QueueNotice)}, body=BotAction | None),
    *(
        OperationContract("GET", path, {200: json_response(ItemsResponse[ConnectorReference])}, query=ListQuery)
        for path in ("/assess/connectors", "/assess/story/{connector_id}/share")
    ),
    *(
        OperationContract("POST", path, {200: json_response(QueueNotice)}, body=ShareInput)
        for path in ("/assess/connectors", "/assess/story/{connector_id}/share")
    ),
    OperationContract("GET", "/assess/connectors/proposals", {200: json_response(CountResponse)}),
    OperationContract("GET", "/assess/stories/{story_id}/revisions", {200: json_response(PageResponse[Revision])}),
    OperationContract(
        "GET", "/assess/stories/{story_id}/revisions/{revision_number}", {200: json_response(RevisionData)}, parameters=StoryRevisionPath
    ),
    OperationContract(
        "POST",
        "/assess/import",
        {200: json_response(ImportedStories | ImportedNews)},
        body=Annotated[JsonValue, BeforeValidator(validate_import)],
    ),
    OperationContract("GET", "/assess/bookmarks", {200: json_response(PageResponse[assess.StoryBookmark])}, query=ListQuery),
    OperationContract("POST", "/assess/bookmarks", {201: json_response(BookmarkWritten)}, body=assess.StoryBookmarkCreatePayload),
    OperationContract("GET", "/assess/bookmarks/{bookmark_id}", {200: json_response(assess.StoryBookmark)}),
    OperationContract(
        "PATCH", "/assess/bookmarks/{bookmark_id}", {200: json_response(BookmarkWritten)}, body=assess.StoryBookmarkUpdatePayload
    ),
    OperationContract("DELETE", "/assess/bookmarks/{bookmark_id}", {200: json_response(MessageResponse)}),
    OperationContract("PATCH", "/assess/bookmarks/order", {200: json_response(MessageResponse)}, body=assess.StoryBookmarkOrderPayload),
    OperationContract("POST", "/assess/bookmarks/quick-save", {200: json_response(BookmarkSaved)}, body=assess.StoryBookmarkStoryPayload),
    OperationContract(
        "POST",
        "/assess/bookmarks/memberships",
        {200: json_response(MessageResponse)},
        body=assess.StoryBookmarkMembershipPayload,
    ),
    OperationContract(
        "POST",
        "/assess/bookmarks/{bookmark_id}/stories",
        {200: json_response(BookmarkAdded)},
        body=assess.StoryBookmarkStoryPayload,
    ),
    OperationContract(
        "POST",
        "/assess/bookmarks/{bookmark_id}/stories/remove",
        {200: json_response(BookmarkRemoved)},
        body=assess.StoryBookmarkStoryPayload,
    ),
)

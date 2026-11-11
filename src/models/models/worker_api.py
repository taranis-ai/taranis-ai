"""Worker-facing HTTP operations and callback contracts."""

from datetime import datetime

from pydantic import BaseModel, Field, JsonValue, StrictBool, TypeAdapter, create_model

from models import admin, assess
from models.api import FileUpload, ItemsResponse, MessageResponse, OperationContract, download_response, json_response
from models.base import TaranisBaseModel
from models.config_api import BotQuery, CronJobsResponse, QueueNotice, WordListQuery
from models.content_api import (
    CollectionError,
    CollectionResult,
    ContentError,
    ContentQuery,
    MispError,
    MispResult,
    NewsConflictError,
    PartialTags,
    StoryAdded,
    StoryInput,
    StoryResponse,
    StoryUpdated,
    Tag,
)
from models.cti import CTIItem
from models.imports import CSV_WORD_LIST, WordListImport
from models.llm import LLMEndpoint, LLMProvider
from models.report import ReportItem
from models.task import TaskChangeNotice


SourceResponse = create_model("WorkerSourceResponse", __base__=admin.OSINTSource, id=(str, ...))


class SourcesResponse(BaseModel):
    sources: list[SourceResponse]


WorkerBot = create_model("WorkerBotResponse", __base__=admin.Bot, id=(str, ...), llm_endpoint=(LLMEndpoint | None, None))
WorkerConnector = create_model("WorkerConnectorResponse", __base__=admin.Connector, id=(str, ...))
WorkerPublisher = create_model("WorkerPublisherResponse", __base__=admin.PublisherPreset, id=(str, ...))
WorkerWordList = create_model("WorkerWordListResponse", __base__=admin.WordList, id=(str, ...))
WorkerReport = create_model("WorkerReportResponse", __base__=ReportItem, id=(str, ...), stories=(list[StoryResponse | str] | None, None))
WorkerProductReport = create_model(
    "WorkerProductReport", __base__=WorkerReport, attributes=(dict[str, dict[str, JsonValue]], Field(default_factory=dict))
)


class WorkerProduct(TaranisBaseModel):
    id: str
    title: str
    description: str | None = None
    type: str
    type_id: str
    mime_type: str
    report_items: list[WorkerProductReport]
    parameters: dict[str, JsonValue]
    render_revision: str


class PipelineRequest(BaseModel):
    filters: dict[str, ContentQuery] = Field(min_length=1)


class PipelineResponse(BaseModel):
    stories: list[StoryResponse]
    selected: dict[str, list[str]]
    revisions: dict[str, int]


class PostCollection(BaseModel):
    source_id: str
    user_id: str | None = None
    story_ids: list[str]


class LastChangeRequest(BaseModel):
    stories: list[str] = Field(default_factory=list)
    news_items: list[str] = Field(default_factory=list)


class IOCQuery(BaseModel):
    # Invalid rows are ignored; valid pairs are looked up without mutation.
    iocs: list[JsonValue] = Field(default_factory=list)


class CheckQuery(BaseModel):
    check_id: str | None = None


class EndpointResult(BaseModel):
    check_id: str
    healthy: StrictBool


class EndpointSkipped(BaseModel):
    skip: bool


class EndpointConfig(BaseModel):
    config: LLMProvider


class EndpointAccepted(BaseModel):
    accepted: bool


class CleanupResult(MessageResponse):
    deleted: int
    cutoff: datetime
    retention_days: int


class ReplaceQuery(BaseModel):
    replace: str = "true"


class WordListUpdated(MessageResponse):
    word_lists: str


class TaranisPublished(MessageResponse):
    url: str


OPERATIONS = (
    OperationContract("GET", "/worker/osint-sources", {200: json_response(SourcesResponse)}),
    OperationContract("GET", "/worker/osint-sources/{source_id}", {200: json_response(SourceResponse)}),
    OperationContract(
        "PUT",
        "/worker/osint-sources/{source_id}/icon",
        {200: json_response(MessageResponse)},
        uploads=FileUpload,
        request_media_types=("multipart/form-data",),
    ),
    OperationContract("GET", "/worker/cron-jobs", {200: json_response(CronJobsResponse)}),
    OperationContract("POST", "/worker/cron-jobs", {200: json_response(MessageResponse)}),
    OperationContract(
        "POST",
        "/worker/tasks/changed",
        {200: json_response(MessageResponse)},
        body=TypeAdapter(TaskChangeNotice),
        validation_error_message="Invalid task change notice",
    ),
    OperationContract("POST", "/worker/tasks/history/cleanup", {200: json_response(CleanupResult)}),
    OperationContract("GET", "/worker/products/{product_id}", {200: json_response(WorkerProduct)}),
    OperationContract("GET", "/worker/products/{product_id}/render", {200: download_response()}),
    OperationContract("GET", "/worker/presenters/{presenter}", {200: download_response()}),
    OperationContract("POST", "/worker/products/{product_id}/publish", {200: json_response(TaranisPublished)}),
    OperationContract("GET", "/worker/publishers/{publisher}", {200: json_response(WorkerPublisher)}),
    OperationContract("GET", "/worker/connectors/{connector_id}", {200: json_response(WorkerConnector)}),
    OperationContract(
        "POST",
        "/worker/news-items",
        {200: json_response(CollectionResult), **{status: json_response(ContentError | CollectionError) for status in (400, 409, 500)}},
        body=TypeAdapter(list[assess.NewsItem]),
        invalid_request_message="Invalid news item data",
    ),
    OperationContract(
        "GET", "/worker/endpoint-health/{kind}/{endpoint_id}", {200: json_response(EndpointSkipped | EndpointConfig)}, query=CheckQuery
    ),
    OperationContract(
        "POST",
        "/worker/endpoint-health/{kind}/{endpoint_id}",
        {200: json_response(EndpointAccepted)},
        body=TypeAdapter(EndpointResult),
        validation_error_message="Invalid endpoint check result",
    ),
    OperationContract("GET", "/worker/bots", {200: json_response(ItemsResponse[WorkerBot])}, query=BotQuery),
    OperationContract("GET", "/worker/bots/{bot_id}", {200: json_response(WorkerBot)}),
    *(
        OperationContract(
            "PUT",
            path,
            {200: json_response(WorkerBot)},
            body=TypeAdapter(admin.BotUpdate),
            validation_error_message="Invalid bot update payload",
        )
        for path in ("/worker/bots", "/worker/bots/{bot_id}")
    ),
    OperationContract("GET", "/worker/tags", {200: json_response(dict[str, Tag])}),
    OperationContract(
        "PUT",
        "/worker/tags",
        {200: json_response(MessageResponse), 207: json_response(PartialTags)},
        body=TypeAdapter(dict[str, JsonValue]),
        query=ReplaceQuery,
    ),
    OperationContract("POST", "/worker/iocs", {200: json_response(ItemsResponse[CTIItem])}, body=TypeAdapter(IOCQuery)),
    OperationContract("PUT", "/worker/post-collection-bots", {200: json_response(QueueNotice)}, body=TypeAdapter(PostCollection)),
    OperationContract(
        "GET",
        "/worker/stories",
        {200: json_response(list[StoryResponse])},
        query=ContentQuery,
        repeated_query=("source", "group", "story_ids"),
    ),
    OperationContract(
        "POST",
        "/worker/stories",
        {
            200: json_response(StoryAdded | StoryUpdated),
            **{status: json_response(ContentError | NewsConflictError) for status in (400, 409, 500)},
        },
        body=TypeAdapter(StoryInput),
    ),
    OperationContract(
        "POST",
        "/worker/bot-pipeline/stories",
        {200: json_response(PipelineResponse)},
        body=TypeAdapter(PipelineRequest),
        validation_error_message="Invalid bot pipeline filters",
    ),
    *(
        OperationContract(
            "POST",
            path,
            {200: json_response(MispResult | MispError), **{status: json_response(ContentError | MispError) for status in (400, 409, 500)}},
            body=TypeAdapter(list[StoryInput]),
        )
        for path in ("/worker/misp/stories", "/worker/misp/last-change")
    ),
    *(
        OperationContract("PUT", path, {200: json_response(MessageResponse)}, body=TypeAdapter(LastChangeRequest))
        for path in ("/worker/misp/stories", "/worker/misp/last-change")
    ),
    *(
        OperationContract(
            "GET",
            path,
            {200: json_response(ItemsResponse[WorkerWordList] if path.endswith("word-lists") else WorkerWordList)},
            query=WordListQuery,
        )
        for path in ("/worker/word-lists", "/worker/word-list/{word_list_id}")
    ),
    *(
        OperationContract(
            "PUT",
            path,
            {200: json_response(WordListUpdated)},
            body=TypeAdapter(WordListImport),
            alternate_bodies={"text/csv": CSV_WORD_LIST},
            request_media_types=("application/json", "text/csv"),
        )
        for path in ("/worker/word-lists", "/worker/word-list/{word_list_id}")
    ),
    OperationContract("GET", "/worker/report-items/{report_id}", {200: json_response(WorkerReport)}),
)

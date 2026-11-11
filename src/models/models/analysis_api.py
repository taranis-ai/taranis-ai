"""Report creation, editing, locking and publishing operation contracts."""

from typing import Literal

from pydantic import BaseModel, Field, JsonValue, StrictBool, TypeAdapter, create_model

from models.api import ErrorResponse, IdMessageResponse, ItemsResponse, MessageResponse, OperationContract, PageResponse, json_response
from models.base import TaranisBaseModel
from models.config_api import QueueNotice
from models.content_api import (
    BotAction,
    ContentError,
    ContentQuery,
    ReportLock,
    ReportRevisionPath,
    Revision,
    RevisionData,
    StoryIds,
    StoryResponse,
)
from models.cti import CTIResponse
from models.product import Product
from models.report import ReportEditor, ReportItem, ReportTypes


class StoryReference(BaseModel):
    id: str


class ReportCreate(TaranisBaseModel):
    title: str = Field(min_length=1)
    report_item_type_id: str = Field(min_length=1)
    completed: StrictBool = False
    stories: list[str | StoryReference] = Field(default_factory=list)
    id: str | None = None


class ReportUpdate(TaranisBaseModel):
    title: str | None = None
    completed: StrictBool | None = None
    attributes: dict[str, JsonValue] | None = None
    stories: list[str | StoryReference] | None = None
    story_ids: list[str | StoryReference] | None = None


ReportResponse = create_model("ReportResponse", __base__=ReportItem, id=(str, ...), stories=(list[StoryResponse | str] | None, None))


class ReportWritten(IdMessageResponse):
    report: ReportResponse


class ReportStoriesWritten(MessageResponse):
    report: ReportResponse | ErrorResponse


class ReportWriteError(MessageResponse):
    id: str | None
    report: ErrorResponse


class ReportStories(BaseModel):
    report: StoryIds


class AttributeOverride(BaseModel):
    group_title: str
    title: str = Field(min_length=1)
    value: JsonValue


class WorkflowReport(ReportCreate):
    story_ids: list[str] | None = None
    attribute_overrides: list[AttributeOverride] | None = None


class WorkflowProduct(TaranisBaseModel):
    title: str = Field(min_length=1)
    product_type_id: str = Field(min_length=1)
    default_publisher: str = Field(min_length=1)
    description: str | None = None


class WorkflowRequest(BaseModel):
    report: WorkflowReport
    product: WorkflowProduct


class PublishResult(BaseModel):
    status: Literal["scheduled", "failed"]
    publisher_id: str
    message: str | None = None
    error: str | None = None


class WorkflowResponse(MessageResponse):
    report: ReportResponse
    product: Product
    publish: PublishResult


OPERATIONS = (
    OperationContract("GET", "/analyze/report-types", {200: json_response(ItemsResponse[ReportTypes])}),
    OperationContract("GET", "/analyze/report-editors/{report_item_id}", {200: json_response(ReportEditor)}),
    *(
        OperationContract("GET", path, {200: json_response(PageResponse[ReportResponse])}, query=ContentQuery, repeated_query=("group",))
        for path in ("/analyze/report-items", "/analyze/reports")
    ),
    *(
        OperationContract("POST", path, {200: json_response(ReportWritten)}, body=TypeAdapter(ReportCreate))
        for path in ("/analyze/report-items", "/analyze/reports")
    ),
    *(OperationContract(method, path, {}) for path in ("/analyze/report-items", "/analyze/reports") for method in ("PUT", "DELETE")),
    *(
        OperationContract("GET", path, {200: json_response(ReportResponse)})
        for path in ("/analyze/report-items/{report_item_id}", "/analyze/report/{report_item_id}")
    ),
    *(
        OperationContract(
            "PUT",
            path,
            {
                200: json_response(ReportWritten),
                **{status: json_response(ReportWriteError | ErrorResponse) for status in (400, 403, 404, 409, 500)},
            },
            body=TypeAdapter(ReportUpdate),
        )
        for path in ("/analyze/report-items/{report_item_id}", "/analyze/report/{report_item_id}")
    ),
    *(
        OperationContract("DELETE", path, {200: json_response(MessageResponse)})
        for path in ("/analyze/report-items/{report_item_id}", "/analyze/report/{report_item_id}")
    ),
    OperationContract("GET", "/analyze/report-items/{report_item_id}/cti", {200: json_response(CTIResponse)}),
    OperationContract("POST", "/analyze/report-items/{report_item_id}/clone", {200: json_response(ReportWritten)}),
    OperationContract("GET", "/analyze/report-items/{report_item_id}/stories", {200: json_response(ReportStories)}),
    *(
        OperationContract(
            method,
            "/analyze/report-items/{report_item_id}/stories",
            {
                200: json_response(MessageResponse | ReportStoriesWritten),
                **{status: json_response(ReportStoriesWritten | ErrorResponse) for status in (400, 403, 404, 409, 500)},
            },
            body=TypeAdapter(list[str]),
        )
        for method in ("PUT", "POST")
    ),
    OperationContract(
        "POST",
        "/analyze/report-items/publish-product",
        {201: json_response(WorkflowResponse), 400: json_response(ContentError), 500: json_response(WorkflowResponse | ErrorResponse)},
        body=TypeAdapter(WorkflowRequest),
    ),
    OperationContract("POST", "/analyze/report-items/botactions", {200: json_response(QueueNotice)}, body=TypeAdapter(BotAction)),
    OperationContract("GET", "/analyze/report-items/{report_item_id}/locks", {200: json_response(ReportLock)}),
    *(
        OperationContract(method, "/analyze/report-items/{report_item_id}/lock", {200: json_response(ReportLock)})
        for method in ("PUT", "DELETE")
    ),
    OperationContract("GET", "/analyze/report-items/{report_item_id}/revisions", {200: json_response(PageResponse[Revision])}),
    OperationContract(
        "GET",
        "/analyze/report-items/{report_item_id}/revisions/{revision_number}",
        {200: json_response(RevisionData)},
        parameters=ReportRevisionPath,
    ),
)

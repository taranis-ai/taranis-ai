"""Configuration HTTP contracts, shared by both administrative route prefixes."""

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, JsonValue, create_model

from models import admin
from models.api import (
    ErrorResponse,
    FileUpload,
    IdMessageResponse,
    ItemsResponse,
    MessageResponse,
    OperationContract,
    PageResponse,
    download_response,
    json_response,
    partial_model,
)
from models.base import TaranisBaseModel
from models.imports import SourceImport, SourcesImported, UsersImported, WordListImport, WordListsImported
from models.scheduler import JobFilter, ScheduledJob
from models.task import Task
from models.types import OSINTState
from models.user import ProfileSettings, UserProfile


class ProfileOrganization(TaranisBaseModel):
    id: str
    name: str


class ProfileRole(TaranisBaseModel):
    id: str
    name: str


UserProfileResponse = create_model(
    "UserProfileResponse",
    __base__=UserProfile,
    id=(str, ...),
    username=(str, ...),
    permissions=(list[str], ...),
    organization=(ProfileOrganization | None, None),
    roles=(list[ProfileRole], Field(default_factory=list)),
)


class ListQuery(BaseModel):
    search: str | None = None
    page: int = 1
    limit: int = 20
    offset: int | None = None
    sort: str | None = None
    order: str | None = None
    fetch_all: bool = False


class SourceQuery(ListQuery):
    type: str | None = None
    filter_manual: bool = False
    state: str | None = None
    period: Literal["day", "week", "month"] | None = None


class BotQuery(ListQuery):
    state: str | None = None


class WordListQuery(ListQuery):
    usage: int | None = None
    with_entries: bool = False


class IdsQuery(BaseModel):
    ids: list[str] = Field(default_factory=list)


class SourceExportQuery(IdsQuery):
    groups: bool = False
    secrets: bool = False


class SourceDeleteQuery(IdsQuery):
    force: Literal["true", "false"] | None = None


WordListResponse = create_model("WordListResponse", __base__=admin.WordList, link=(str | None, ""))


class WordListInput(TaranisBaseModel):
    id: str | None = None
    name: str = ""
    description: str | None = ""
    link: str | None = None
    usage: int | list[str] = 0
    entries: list[admin.WordListEntry] = Field(default_factory=list)


class UserResponse(TaranisBaseModel):
    id: str
    name: str
    username: str
    organization: str | None
    roles: list[str]
    permissions: list[str]
    profile: dict[str, JsonValue] | None = None
    last_login: str | None = None


class UserInput(TaranisBaseModel):
    id: str | None = None
    name: str
    username: str = ""
    organization: str | dict[str, JsonValue] | None = None
    roles: list[str] | None = Field(default_factory=list)
    password: str | None = None
    profile: ProfileSettings | None = None


class SourceUpdate(admin.OSINTSourceUpdateModel):
    state: Literal["enabled", "disabled"] | None = None


class ConnectorUpdate(TaranisBaseModel):
    name: str | None = None
    description: str | None = None
    type: str | None = None
    index: int | None = None
    parameters: dict[str, JsonValue] | None = None
    icon: str | None = None
    state: OSINTState | None = None


class ValidationStatus(TypedDict):
    is_valid: bool
    error_message: str
    error_type: str


class TemplateResponse(BaseModel):
    name: str
    content: str | None
    validation_status: ValidationStatus


class TemplateWrite(BaseModel):
    name: str | None = None
    content: str | None = None


class TemplateValidationRequest(BaseModel):
    content: str = Field(min_length=1)
    is_base64: bool = False


class TemplateWriteResponse(BaseModel):
    message: str
    path: str
    validation_status: ValidationStatus
    warning: str | None = None


class TemplateDeleteResponse(BaseModel):
    message: str
    path: str


class TemplateValidationResponse(ValidationStatus):
    message: str


class DagParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    RUN_AFTER_COLLECTOR: bool | str = False
    RUN_AFTER_BOTS: list[str] | str = Field(default_factory=list)


class DagRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str | None = None
    type: str | None = None
    index: int | str | None = None
    enabled: bool | str = True
    parameters: DagParameters = Field(default_factory=DagParameters)


class DagNode(BaseModel):
    id: str
    type: str
    name: str
    enabled: bool


class DagEdge(BaseModel):
    from_id: str
    from_type: str
    from_name: str
    to_id: str
    to_type: str
    to_name: str
    disabled: bool


class DagResponse(BaseModel):
    order: list[DagNode]
    nodes: list[DagNode]
    edges: list[DagEdge]
    warnings: list[str]


class WorkerInstance(BaseModel):
    name: str
    status: str


class WorkerEntry(BaseModel):
    name: str
    state: str
    queues: list[str]
    current_job: str | None


class WorkerStatsResponse(BaseModel):
    total_workers: int
    busy_workers: int
    idle_workers: int
    workers: list[WorkerEntry]


class QueueStatusResponse(BaseModel):
    status: str
    url: str


class QueueStatusError(ErrorResponse):
    url: str


class CronJobConfig(BaseModel):
    task: str
    queue: str
    args: list[JsonValue]
    cron: str
    task_id: str | None = None
    name: str | None = None


class CronJobsResponse(BaseModel):
    cron_jobs: list[CronJobConfig]


class QueueNotice(BaseModel):
    message: str
    id: str | None = None
    status: str | None = None


class SourceDeleteResponse(BaseModel):
    message: str
    ids: list[str]


class QueuedState(BaseModel):
    id: str
    status: str


class SecretResponse(BaseModel):
    value: str


class CuratedSummary(BaseModel):
    name: str
    description: str
    source_count: int


class CuratedLoadResponse(BaseModel):
    message: str
    created_source_count: int
    reused_source_count: int
    created_group_count: int
    updated_group_count: int


class ReportTypeAttributeInput(TaranisBaseModel):
    id: str | None = None
    title: str
    description: str = ""
    index: int
    attribute_id: str | None = None
    attribute: str | None = None
    required: bool = False


class ReportTypeGroupInput(TaranisBaseModel):
    id: str | None = None
    title: str
    description: str = ""
    index: int
    attribute_group_items: list[ReportTypeAttributeInput] = Field(default_factory=list)


class ReportTypeInput(TaranisBaseModel):
    id: str | None = None
    title: str
    description: str = ""
    attribute_groups: list[ReportTypeGroupInput] | None = Field(default_factory=list)


def _crud_operations() -> list[OperationContract]:
    operations = []
    resources = (
        ("acls", "acl_id", admin.ACL, admin.ACL, None, False, True, ListQuery),
        ("attributes", "attribute_id", admin.Attribute, admin.Attribute, None, False, True, ListQuery),
        ("organizations", "organization_id", admin.Organization, admin.Organization, None, False, True, ListQuery),
        ("roles", "role_id", admin.Role, admin.Role, None, False, True, ListQuery),
        ("users", "user_id", UserResponse, UserInput, None, False, True, ListQuery),
        ("word-lists", "word_list_id", WordListResponse, WordListInput, None, False, True, WordListQuery),
        ("osint-source-groups", "group_id", admin.OSINTSourceGroup, admin.OSINTSourceGroup, None, False, True, ListQuery),
        ("report-item-types", "type_id", admin.ReportItemType, ReportTypeInput, None, False, True, ListQuery),
        ("bots", "bot_id", admin.Bot, admin.BotCreate, admin.BotUpdate, True, False, BotQuery),
        ("osint-sources", "source_id", admin.OSINTSource, admin.OSINTSource, SourceUpdate, True, False, SourceQuery),
        ("sources", "source_id", admin.OSINTSource, admin.OSINTSource, SourceUpdate, True, False, SourceQuery),
        ("product-types", "type_id", admin.ProductType, admin.ProductType, None, True, False, ListQuery),
        ("publisher-presets", "preset_id", admin.PublisherPreset, admin.PublisherPreset, None, True, False, ListQuery),
        ("publishers-presets", "preset_id", admin.PublisherPreset, admin.PublisherPreset, None, True, False, ListQuery),
        ("connectors", "connector_id", admin.Connector, admin.Connector, ConnectorUpdate, True, False, ListQuery),
    )
    for prefix in ("config", "admin"):
        for resource, identifier, response, creation, update, patch, collection_crud, query in resources:
            response = create_model(f"{response.__name__}ResourceResponse", __base__=response, id=(str, ...))
            detail_response = UserProfileResponse if resource == "users" else response
            update = update or partial_model(creation)
            path = f"/{prefix}/{resource}"
            detail = f"{path}/{{{identifier}}}"
            operations.extend(
                (
                    OperationContract("GET", path, {200: json_response(PageResponse[response])}, query=query),
                    OperationContract(
                        "POST",
                        path,
                        {200: json_response(IdMessageResponse), 201: json_response(IdMessageResponse)},
                        body=creation,
                    ),
                    OperationContract("GET", detail, {200: json_response(detail_response)}, query=query),
                    OperationContract(
                        "PUT",
                        detail,
                        {200: json_response(IdMessageResponse), 201: json_response(IdMessageResponse)},
                        body=update,
                    ),
                    OperationContract(
                        "DELETE",
                        detail,
                        {
                            200: json_response(
                                IdMessageResponse if resource in {"sources", "osint-sources", "connectors"} else MessageResponse
                            )
                        },
                        query=SourceDeleteQuery if resource in {"sources", "osint-sources"} else ListQuery,
                    ),
                )
            )
            if patch:
                operations.append(OperationContract("PATCH", detail, {200: json_response(IdMessageResponse)}, body=update))
            if collection_crud:
                operations.extend((OperationContract("PUT", path, {}, body=update), OperationContract("DELETE", path, {})))
    return operations


def _utility_operations() -> list[OperationContract]:
    operations = []
    for prefix in ("config", "admin"):

        def op(method: str, path: str, responses: dict[int, Any], *, prefix=prefix, **kwargs):
            operations.append(OperationContract(method, f"/{prefix}{path}", responses, **kwargs))

        op("GET", "/permissions", {200: json_response(PageResponse[admin.Permission])}, query=ListQuery)
        op("GET", "/templates", {200: json_response(PageResponse[TemplateResponse])}, query=ListQuery)
        op("GET", "/templates/{template_path}", {200: json_response(TemplateResponse)})
        for path in ("/templates", "/templates/{template_path}"):
            op("POST", path, {200: json_response(TemplateWriteResponse)}, body=TemplateWrite)
            op("PUT", path, {200: json_response(TemplateWriteResponse)}, body=TemplateWrite)
            op("DELETE", path, {200: json_response(TemplateDeleteResponse)})
        op("POST", "/templates/validate", {200: json_response(TemplateValidationResponse)}, body=TemplateValidationRequest)
        op(
            "POST",
            "/bots/dag-preview",
            {200: json_response(DagResponse)},
            body=DagRequest,
        )
        op("POST", "/dictionaries-reload/{dictionary_type}", {200: json_response(MessageResponse)})
        for path in (
            "/bots/{bot_id}/execute",
            "/osint-sources/{source_id}/collect",
            "/osint-sources/collect",
            "/connectors/{connector_id}/pull",
            "/word-lists/gather",
            "/word-lists/gather/{word_list_id}",
        ):
            op("POST", path, {200: json_response(QueueNotice), 201: json_response(QueueNotice), 202: json_response(QueueNotice)})
        op(
            "GET",
            "/osint-sources/{source_id}/preview",
            {200: json_response(Task), 201: json_response(QueueNotice), 202: json_response(QueuedState)},
        )
        op("POST", "/osint-sources/{source_id}/preview", {201: json_response(QueueNotice)})
        op("GET", "/osint-source-groups/options", {200: json_response(admin.OSINTSourceGroupOptions)})
        op("GET", "/curated-osint-source-lists", {200: json_response(ItemsResponse[CuratedSummary])})
        op(
            "POST",
            "/curated-osint-source-lists",
            {200: json_response(CuratedLoadResponse)},
            body=admin.CuratedOSINTSourceSelection,
        )
        op("DELETE", "/osint-sources", {200: json_response(SourceDeleteResponse)}, query=SourceDeleteQuery, repeated_query=("ids",))
        op("GET", "/workers", {200: json_response(list[WorkerInstance])})
        op("GET", "/workers/queue-status", {200: json_response(QueueStatusResponse), 500: json_response(QueueStatusError)})
        op("GET", "/workers/tasks", {200: json_response(list[admin.QueueStatus])})
        op("GET", "/workers/stats", {200: json_response(WorkerStatsResponse)})
        op("GET", "/workers/cron-jobs", {200: json_response(CronJobsResponse)})
        op("GET", "/admin-menu-badges", {200: json_response(admin.AdminMenuBadges)})
        for path, model in (
            ("/workers/active", admin.ActiveJob),
            ("/workers/failed", admin.FailedJob),
            ("/schedule", ScheduledJob),
            ("/workers/schedule", ScheduledJob),
        ):
            op("GET", path, {200: json_response(PageResponse[model])}, query=JobFilter)
        op("GET", "/schedule/{task_id}", {200: json_response(ScheduledJob)})
        op("POST", "/parameter-secrets/{resource}/{resource_id}/{parameter}/reveal", {200: json_response(SecretResponse)})
        for path in ("/users-export", "/export-word-lists", "/export-report-item-types"):
            op("GET", path, {200: download_response("application/json")}, query=IdsQuery, repeated_query=("ids",))
        op("GET", "/export-osint-sources", {200: download_response("application/json")}, query=SourceExportQuery, repeated_query=("ids",))
        op(
            "POST",
            "/import-osint-sources",
            {200: json_response(SourcesImported)},
            body=SourceImport,
            uploads=FileUpload,
            file_body=True,
            request_media_types=("application/json", "multipart/form-data"),
        )
        op(
            "POST",
            "/import-word-lists",
            {200: json_response(WordListsImported)},
            body=WordListImport,
            uploads=FileUpload,
            file_body=True,
            alternate_bodies={"text/csv": str},
            request_media_types=("application/json", "multipart/form-data"),
        )
        # Malformed rows are deliberately skipped individually by the import service.
        op(
            "POST",
            "/users-import",
            {200: json_response(UsersImported)},
            body=list[JsonValue],
        )
        op("POST", "/import-report-item-types", {})
    return operations


OPERATIONS = tuple(_crud_operations() + _utility_operations())

"""Reviewed executable operation definitions; paths are relative to the Core API."""

from typing import Any, Literal
from urllib.parse import parse_qs, urlsplit

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from models.analysis_api import OPERATIONS as ANALYSIS_OPERATIONS
from models.api import ErrorResponse, MessageResponse, OperationContract, json_response
from models.assessment_api import OPERATIONS as ASSESSMENT_OPERATIONS
from models.base import TaranisBaseModel
from models.bot_api import OPERATIONS as BOT_OPERATIONS
from models.chat import ChatConversation, ChatConversationList, ChatConversationSummary, ChatMessage, ChatTurnRequest
from models.config_api import OPERATIONS as CONFIG_OPERATIONS
from models.connector_api import OPERATIONS as CONNECTOR_OPERATIONS
from models.dashboard import CoreHealth
from models.realtime_api import OPERATIONS as REALTIME_OPERATIONS
from models.task import (
    Task,
    TaskHistoryStats,
    TaskHistoryTotals,
    TaskResult,
    TaskRunFilter,
    TaskSubmission,
    UserTask,
    UserTaskFilter,
    UserTaskList,
)
from models.worker_api import OPERATIONS as WORKER_OPERATIONS
from models.workspace_api import OPERATIONS as WORKSPACE_OPERATIONS


class IsAliveResponse(BaseModel):
    isalive: Literal[True]


class TaskPath(BaseModel):
    task_id: str = Field(min_length=1)


class ConversationPath(BaseModel):
    conversation_id: str = Field(min_length=1)


class PendingTaskResponse(BaseModel):
    status: Literal["PENDING"]


class TaskQuery(BaseModel):
    search: str | None = None
    page: int = 1
    limit: int = 20
    sort: str | None = None
    order: str | None = None
    fetch_all: bool = False


class TaskResponse(Task):
    result: TaskResult | None
    status: str | None


class TaskListResponse(TaranisBaseModel):
    items: list[TaskResponse]
    total_count: int = Field(ge=0)
    task_stats: dict[str, TaskHistoryStats]
    totals: TaskHistoryTotals


class UserTaskListResponse(UserTaskList):
    items: list[UserTask]
    total_count: int = Field(ge=0)


class ConversationListResponse(ChatConversationList):
    items: list[ChatConversationSummary]


class ConversationResponse(ChatConversation):
    messages: list[ChatMessage]


class TurnResponse(TaranisBaseModel):
    conversation: ConversationResponse


class AccessTokenResponse(BaseModel):
    access_token: str = Field(min_length=1)


class ExternalAuthHeaders(BaseModel):
    username_header: str
    roles_header: str
    name_header: str
    organization_header: str


class AuthMethodResponse(BaseModel):
    auth_method: Literal["database", "dev", "openid", "external"]
    auth_headers: ExternalAuthHeaders | None = None


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    current_password: str = ""
    new_password: str = ""
    confirm_password: str = ""


OPERATIONS = (
    (
        OperationContract("GET", "/", {200: json_response(IsAliveResponse)}),
        OperationContract("GET", "/isalive", {200: json_response(IsAliveResponse)}),
        OperationContract("GET", "/health", {200: json_response(CoreHealth), 503: json_response(CoreHealth)}),
        OperationContract("GET", "/tasks", {200: json_response(TaskListResponse)}, query=TaskQuery),
        OperationContract("POST", "/tasks", {200: json_response(TaskResponse)}, body=TypeAdapter(TaskSubmission)),
        OperationContract("DELETE", "/tasks", {}),
        OperationContract(
            "GET",
            "/tasks/{task_id}",
            {200: json_response(TaskResponse), 404: json_response(PendingTaskResponse | ErrorResponse)},
            parameters=TaskPath,
        ),
        OperationContract("DELETE", "/tasks/{task_id}", {200: json_response(MessageResponse)}, parameters=TaskPath),
        OperationContract("GET", "/tasks/user", {200: json_response(UserTaskListResponse)}, query=UserTaskFilter),
        OperationContract("GET", "/tasks/runs", {200: json_response(UserTaskListResponse)}, query=TaskRunFilter, repeated_query=("job_ids",)),
        OperationContract("GET", "/auth/refresh", {200: json_response(AccessTokenResponse)}),
        OperationContract("DELETE", "/auth/logout", {200: json_response(MessageResponse)}),
        OperationContract("GET", "/auth/method", {200: json_response(AuthMethodResponse)}),
        OperationContract("POST", "/auth/change_password", {200: json_response(MessageResponse)}, body=TypeAdapter(ChangePasswordRequest)),
        OperationContract("GET", "/chat/conversations", {200: json_response(ConversationListResponse)}),
        OperationContract("POST", "/chat/conversations", {201: json_response(TurnResponse)}, body=TypeAdapter(ChatTurnRequest)),
        OperationContract(
            "GET", "/chat/conversations/{conversation_id}", {200: json_response(ConversationResponse)}, parameters=ConversationPath
        ),
        OperationContract(
            "DELETE", "/chat/conversations/{conversation_id}", {200: json_response(MessageResponse)}, parameters=ConversationPath
        ),
        OperationContract(
            "POST",
            "/chat/conversations/{conversation_id}/messages",
            {201: json_response(TurnResponse)},
            body=TypeAdapter(ChatTurnRequest),
            parameters=ConversationPath,
        ),
    )
    + ASSESSMENT_OPERATIONS
    + ANALYSIS_OPERATIONS
    + BOT_OPERATIONS
    + CONNECTOR_OPERATIONS
    + REALTIME_OPERATIONS
    + CONFIG_OPERATIONS
    + WORKSPACE_OPERATIONS
    + WORKER_OPERATIONS
)


def find_operation(method: str, path: str) -> OperationContract | None:
    # Literal routes must win over identifier routes such as /tasks/{task_id}.
    for operation in sorted(OPERATIONS, key=lambda operation: "{" in operation.path):
        if operation.match(method, path) is not None:
            return operation
    return None


def validate_outgoing_request(
    method: str,
    path: str,
    payload: Any = None,
    params: dict | None = None,
    *,
    content_type: str = "application/json",
    files: dict | None = None,
    headers: dict | None = None,
) -> OperationContract:
    operation = find_operation(method, path)
    if operation is None:
        raise ValueError("Missing API operation contract")
    if files is not None:
        if operation.uploads is None:
            raise ValueError("Unexpected upload")
        metadata = {
            name: {
                "filename": item[0],
                "content_type": item[2] if len(item) > 2 else None,
                "content_length": len(item[1]) if isinstance(item[1], (str, bytes)) else None,
            }
            for name, item in files.items()
        }
        operation.uploads.model_validate(metadata)
    elif content_type in operation.alternate_bodies:
        operation.alternate_bodies[content_type].validate_python(payload.decode("utf-8") if isinstance(payload, bytes) else payload)
    else:
        operation.validate_body(payload)
    values = parse_qs(urlsplit(path).query, keep_blank_values=True)
    for key, value in (params or {}).items():
        entries = value if isinstance(value, (list, tuple)) else [value]
        entries = [entry for entry in entries if entry is not None]
        if entries:
            values.setdefault(key, []).extend(str(entry) for entry in entries)
    query = {key: value if key in operation.repeated_query else value[0] for key, value in values.items()}
    operation.query.model_validate(query)
    operation.parameters.model_validate(operation.match(method, path))
    operation.headers.model_validate(headers or {})
    return operation

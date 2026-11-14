"""Static Core API inventory; paths are relative to the configured API prefix.

This module does not match URLs or validate HTTP traffic. Shared error payloads
are in models.api.ERROR_RESPONSES; endpoint-specific responses take precedence.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from models.analysis_api import OPERATIONS as ANALYSIS_OPERATIONS
from models.api import ApiEndpointModels, ErrorResponse, MessageResponse, json_response
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


_OPERATIONS = (
    (
        ApiEndpointModels("GET", "/", {200: json_response(IsAliveResponse)}),
        ApiEndpointModels("GET", "/isalive", {200: json_response(IsAliveResponse)}),
        ApiEndpointModels("GET", "/health", {200: json_response(CoreHealth), 503: json_response(CoreHealth)}),
        ApiEndpointModels("GET", "/tasks", {200: json_response(TaskListResponse)}, query=TaskQuery),
        ApiEndpointModels("POST", "/tasks", {200: json_response(TaskResponse)}, body=TaskSubmission),
        ApiEndpointModels("DELETE", "/tasks", {}),
        ApiEndpointModels(
            "GET",
            "/tasks/{task_id}",
            {200: json_response(TaskResponse), 404: json_response(PendingTaskResponse | ErrorResponse)},
            parameters=TaskPath,
        ),
        ApiEndpointModels("DELETE", "/tasks/{task_id}", {200: json_response(MessageResponse)}, parameters=TaskPath),
        ApiEndpointModels("GET", "/tasks/user", {200: json_response(UserTaskListResponse)}, query=UserTaskFilter),
        ApiEndpointModels("GET", "/tasks/runs", {200: json_response(UserTaskListResponse)}, query=TaskRunFilter, repeated_query=("job_ids",)),
        ApiEndpointModels("GET", "/auth/refresh", {200: json_response(AccessTokenResponse)}),
        ApiEndpointModels("DELETE", "/auth/logout", {200: json_response(MessageResponse)}),
        ApiEndpointModels("GET", "/auth/method", {200: json_response(AuthMethodResponse)}),
        ApiEndpointModels("POST", "/auth/change_password", {200: json_response(MessageResponse)}, body=ChangePasswordRequest),
        ApiEndpointModels("GET", "/chat/conversations", {200: json_response(ConversationListResponse)}),
        ApiEndpointModels("POST", "/chat/conversations", {201: json_response(TurnResponse)}, body=ChatTurnRequest),
        ApiEndpointModels(
            "GET", "/chat/conversations/{conversation_id}", {200: json_response(ConversationResponse)}, parameters=ConversationPath
        ),
        ApiEndpointModels(
            "DELETE", "/chat/conversations/{conversation_id}", {200: json_response(MessageResponse)}, parameters=ConversationPath
        ),
        ApiEndpointModels(
            "POST",
            "/chat/conversations/{conversation_id}/messages",
            {201: json_response(TurnResponse)},
            body=ChatTurnRequest,
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


# Keys are exact contract templates, not URL matching rules.
OPERATIONS = {(operation.method, operation.path): operation for operation in _OPERATIONS}

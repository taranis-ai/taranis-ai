from functools import wraps

from flask import g, make_response, request
from flask_jwt_extended import current_user
from flask_openapi import APIBlueprint, OpenAPI, validate_request
from models.task import (
    MissingTaskResponse,
    TaskDeleteResponse,
    TaskErrorResponse,
    TaskHistoryFilter,
    TaskHistoryResponse,
    TaskPath,
    TaskResponse,
    TaskRunFilter,
    TaskSubmission,
    UserTaskFilter,
    UserTaskList,
)
from pydantic import ValidationError

from core.config import Config
from core.log import logger
from core.managers.auth_manager import api_key_or_auth_required, api_key_required, auth_required
from core.service.task import TaskService


def task_validation_error(error: ValidationError):
    model = TaskSubmission if request.method == "POST" else TaskHistoryFilter
    return make_response({"error": model.format_validation_errors(error)}, 400)


def _require_json_object(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        # shortcut: flask-openapi 5.0.0 decodes JSON strings twice, remove this guard once fixed and the error body is preserved.
        if not isinstance(request.get_json(silent=True), dict):
            return {"error": "No data provided"}, 400
        return view(*args, **kwargs)

    return wrapper


def initialize(app: OpenAPI):
    worker_or_user = [{"APIKey": []}, {"UserAuth": []}]
    task_bp = APIBlueprint(
        "tasks",
        __name__,
        url_prefix=f"{Config.APPLICATION_ROOT}api/tasks",
        abp_responses={400: TaskErrorResponse, 401: TaskErrorResponse},
    )

    @task_bp.get(
        "",
        endpoint="tasks",
        operation_id="tasks.tasks.get",
        summary="List task history and statistics",
        tags=[{"name": "config"}],
        security=worker_or_user,
        responses={200: TaskHistoryResponse, 403: TaskErrorResponse},
    )
    @api_key_or_auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    @validate_request()
    def get_tasks(query: TaskHistoryFilter):
        return TaskService.get_tasks(filter_args=query.model_dump(exclude_none=True), user=g.authenticated_user)

    @task_bp.post(
        "",
        endpoint="tasks_post",
        operation_id="tasks.tasks.post",
        summary="Submit a worker task result",
        tags=[{"name": "config"}],
        security=[{"APIKey": []}],
        responses={200: TaskResponse, 409: TaskErrorResponse},
    )
    @api_key_required
    @_require_json_object
    @validate_request()
    def submit_task(body: TaskSubmission):
        logger.debug(f"Received task result with id {body.id} and status {body.status}")
        return TaskService.save_task_result(body)

    @task_bp.delete(
        "",
        endpoint="tasks_delete",
        operation_id="tasks.tasks.delete",
        summary="Reject task deletion without a task ID",
        tags=[{"name": "config"}],
        security=worker_or_user,
        responses={403: TaskErrorResponse},
    )
    @api_key_or_auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    def delete_without_id():
        return {"error": "No task_id provided"}, 400

    @task_bp.get(
        "/runs",
        endpoint="completed_runs",
        operation_id="tasks.completed_runs.get",
        summary="List completed runs",
        description="List completed jobs and committed pipeline steps. Private result data is omitted and failure messages are curated.",
        tags=[{"name": "tasks"}],
        security=worker_or_user,
        responses={200: UserTaskList, 403: TaskErrorResponse},
    )
    @api_key_or_auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    @validate_request()
    def get_completed_runs(query: TaskRunFilter):
        return TaskService.get_completed_runs(query)

    @task_bp.get(
        "/user",
        endpoint="user_tasks",
        operation_id="tasks.user_tasks.get",
        summary="List the authenticated user's tasks",
        description="List queued, running, and completed tasks triggered by the authenticated user.",
        tags=[{"name": "tasks"}],
        security=[{"UserAuth": []}],
        responses={200: UserTaskList},
    )
    @auth_required()
    @validate_request()
    def get_user_tasks(query: UserTaskFilter):
        return TaskService.get_user_tasks(current_user.id, query)

    @task_bp.get(
        "/<string:task_id>",
        endpoint="task",
        operation_id="tasks.task.get",
        summary="Get a task result",
        tags=[{"name": "config"}],
        security=worker_or_user,
        responses={200: TaskResponse, 403: TaskErrorResponse, 404: MissingTaskResponse},
    )
    @api_key_or_auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    @validate_request()
    def get_task(path: TaskPath):
        return TaskService.get_task(path.task_id)

    @task_bp.delete(
        "/<string:task_id>",
        endpoint="task_delete",
        operation_id="tasks.task.delete",
        summary="Delete a task result",
        tags=[{"name": "config"}],
        security=worker_or_user,
        responses={200: TaskDeleteResponse, 403: TaskErrorResponse, 404: TaskErrorResponse},
    )
    @api_key_or_auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    @validate_request()
    def delete_task(path: TaskPath):
        return TaskService.delete_task(path.task_id)

    app.register_api(task_bp)

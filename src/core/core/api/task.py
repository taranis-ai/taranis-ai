from typing import Any

from flask import Blueprint, Flask, g
from flask.views import MethodView
from flask_jwt_extended import current_user

from core.api.contracts import validate_request
from core.config import Config
from core.log import logger
from core.managers.auth_manager import api_key_or_auth_required, api_key_required, auth_required
from core.managers.decorators import extract_args
from core.service.task import TaskService


class Task(MethodView):
    @api_key_or_auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order", "fetch_all")
    @validate_request
    def get(self, task_id: str | None = None, filter_args: dict[str, Any] | None = None):
        if task_id:
            return TaskService.get_task(task_id)
        return TaskService.get_tasks(filter_args=g.api_query.model_dump(exclude_unset=True), user=getattr(g, "authenticated_user", None))

    @api_key_required
    @validate_request
    def post(self):
        submission = g.api_body
        logger.debug(f"Received task result with id {submission.id} and status {submission.status}")
        return TaskService.save_task_result(submission)

    @api_key_or_auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    @validate_request
    def delete(self, task_id: str | None = None):
        if not task_id:
            return {"error": "No task_id provided"}, 400
        return TaskService.delete_task(task_id)


class UserTasks(MethodView):
    @auth_required()
    @extract_args("search", "page", "limit", "order")
    @validate_request
    def get(self, filter_args: dict[str, Any] | None = None):
        return TaskService.get_user_tasks(current_user.id, g.api_query)


class CompletedRuns(MethodView):
    @api_key_or_auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    @extract_args("search", "page", "limit", "order", "status")
    @validate_request
    def get(self, filter_args: dict[str, Any] | None = None):
        return TaskService.get_completed_runs(g.api_query)


def initialize(app: Flask):
    task_bp = Blueprint("tasks", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/tasks")
    task_bp.add_url_rule("", view_func=Task.as_view("tasks"))
    task_bp.add_url_rule("/runs", view_func=CompletedRuns.as_view("completed_runs"), methods=["GET"])
    task_bp.add_url_rule("/user", view_func=UserTasks.as_view("user_tasks"), methods=["GET"])
    task_bp.add_url_rule("/<string:task_id>", view_func=Task.as_view("task"), methods=["GET", "DELETE"])
    app.register_blueprint(task_bp)

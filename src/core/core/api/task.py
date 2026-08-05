from typing import Any

from flask import Blueprint, Flask, g, request
from flask.views import MethodView
from flask_jwt_extended import current_user
from models.task import TaskSubmission
from pydantic import ValidationError

from core.config import Config
from core.log import logger
from core.managers.auth_manager import api_key_or_auth_required, api_key_required, auth_required
from core.managers.decorators import extract_args
from core.service.task import TaskService


class Task(MethodView):
    @api_key_or_auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order", "fetch_all")
    def get(self, task_id: str | None = None, filter_args: dict[str, Any] | None = None):
        if task_id:
            return TaskService.get_task(task_id)
        return TaskService.get_tasks(filter_args=filter_args, user=getattr(g, "authenticated_user", None))

    @api_key_required
    def post(self):
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return {"error": "No data provided"}, 400

        try:
            submission = TaskSubmission.model_validate(payload)
        except ValidationError as exc:
            return {"error": TaskSubmission.format_validation_errors(exc)}, 400

        logger.debug(f"Received task result with id {submission.id} and status {submission.status}")
        return TaskService.save_task_result(submission)

    @api_key_or_auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    def delete(self, task_id: str | None = None):
        if not task_id:
            return {"error": "No task_id provided"}, 400
        return TaskService.delete_task(task_id)


class UserTasks(MethodView):
    @auth_required()
    @extract_args("search", "page", "limit", "order")
    def get(self, filter_args: dict[str, Any] | None = None):
        return TaskService.get_user_tasks(current_user.id, filter_args)


def initialize(app: Flask):
    task_bp = Blueprint("tasks", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/tasks")
    task_bp.add_url_rule("", view_func=Task.as_view("tasks"))
    task_bp.add_url_rule("/user", view_func=UserTasks.as_view("user_tasks"), methods=["GET"])
    task_bp.add_url_rule("/<string:task_id>", view_func=Task.as_view("task"), methods=["GET", "DELETE"])
    app.register_blueprint(task_bp)

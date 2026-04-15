from typing import Any

from flask import Blueprint, Flask, request
from flask.views import MethodView
from models.task import TaskSubmission
from pydantic import ValidationError

from core.config import Config
from core.log import logger
from core.managers.auth_manager import api_key_or_auth_required, api_key_required
from core.managers.decorators import extract_args
from core.service.task import TaskService


class Task(MethodView):
    @api_key_or_auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    @extract_args("search", "page", "limit", "sort", "order", "fetch_all")
    def get(self, task_id: str | None = None, filter_args: dict[str, Any] | None = None):
        if task_id:
            return TaskService.get_task(task_id)
        return TaskService.get_tasks(filter_args=filter_args, user=None)

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
    def delete(self, task_id: str):
        return TaskService.delete_task(task_id)


def initialize(app: Flask):
    task_bp = Blueprint("tasks", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/tasks")
    task_bp.add_url_rule("", view_func=Task.as_view("tasks"))
    task_bp.add_url_rule("/<string:task_id>", view_func=Task.as_view("task"))
    app.register_blueprint(task_bp)

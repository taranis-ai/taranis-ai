# type: ignore

from datetime import datetime
from typing import Any

from flask import Blueprint, Flask, request
from flask.views import MethodView

from core.config import Config
from core.log import logger
from core.managers.auth_manager import api_key_required
from core.model.product import Product
from core.model.task import Task as TaskModel
from core.model.token_blacklist import TokenBlacklist
from core.model.word_list import WordList
from core.service.misp_story_sync import handle_misp_connector_result
from core.service.news_item_tag import NewsItemTagService


TAGGING_BOTS = {"WORDLIST_BOT", "IOC_BOT", "NLP_BOT", "TAGGING_BOT"}


class Task(MethodView):
    @api_key_required
    def get(self, task_id: str):
        if result := TaskModel.get(task_id):
            return result.to_dict(), 200
        return {"status": "PENDING"}, 404

    @api_key_required
    def post(self):
        data = request.json
        if not data or "task_id" not in data:
            return {"error": "task_id not found"}, 400

        task_id = data["task_id"]
        result = data.get("result")
        status = data.get("status")
        task_name = data.get("task", "")

        logger.debug(f"Received task result with id {task_id} and status {status}")

        if status == "SUCCESS" and result is not None:
            handle_task_result(task_id=task_id, task_name=task_name, result=result)

        TaskModel.add_or_update(
            {
                "id": task_id,
                "result": serialize_result(result, task_name),
                "status": status,
                "task": task_name,
            }
        )
        return {"status": status}, 200


def initialize(app: Flask):
    task_bp = Blueprint("tasks", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/tasks")
    task_bp.add_url_rule("", view_func=Task.as_view("tasks"))
    task_bp.add_url_rule("/<string:task_id>", view_func=Task.as_view("task"))
    app.register_blueprint(task_bp)


def serialize_result(result: dict[str, Any] | str | None, task_name: str | None = None) -> Any:
    if result is None:
        return None

    if isinstance(result, str):
        return result

    if task_name == "connector_task":
        return result

    exc_message = result.get("exc_message")
    if exc_message:
        if isinstance(exc_message, (list, tuple)):
            return " ".join(map(str, exc_message))
        return exc_message

    return result.get("message", result)


def resolve_task_kind(task_id: str, task_name: str | None) -> str | None:
    task_name = task_name or ""

    if task_name == "gather_word_list" or task_id.startswith("gather_word_list"):
        return "gather_word_list"
    if task_name == "cleanup_token_blacklist" or task_id.startswith("cleanup_token_blacklist"):
        return "cleanup_token_blacklist"
    if task_name == "presenter_task" or task_id.startswith("presenter_task"):
        return "presenter_task"
    if task_name == "collector_task" or task_name.startswith("collect_") or task_id.startswith("collect_"):
        return "collector_task"
    if task_name == "bot_task" or task_name.startswith("bot_") or task_id.startswith("bot"):
        return "bot_task"
    if task_name == "connector_task":
        return "connector_task"

    return None


def handle_task_result(task_id: str, task_name: str, result: dict[str, Any] | str) -> None:
    task_kind = resolve_task_kind(task_id, task_name)
    if not task_kind:
        return

    if task_kind == "cleanup_token_blacklist":
        TokenBlacklist.delete_older(datetime.now() - Config.JWT_ACCESS_TOKEN_EXPIRES)
        return

    if task_kind == "collector_task":
        logger.info(f"Collector task {task_id} completed with result: {result}")
        return

    if task_kind == "connector_task":
        handle_misp_connector_result(result)
        return

    if not isinstance(result, dict):
        logger.error(f"Invalid {task_kind} result type: {type(result)}. Expected dict.")
        return

    if task_kind == "gather_word_list":
        WordList.update_word_list(**result)
        return

    if task_kind == "presenter_task":
        handle_presenter_result(result)
        return

    if task_kind == "bot_task":
        handle_bot_result(result)
        return


def handle_task_specific_result(task_id: str, result: dict[str, Any] | str, status: str, task_name: str | None = None) -> None:
    del status
    handle_task_result(task_id=task_id, task_name=task_name or "", result=result)


def handle_presenter_result(result: dict[str, Any]) -> None:
    product_id = result.get("product_id")
    rendered_product = result.get("render_result")

    if not isinstance(product_id, str) or not isinstance(rendered_product, str):
        logger.error(f"Product {product_id} not found or no render result")
        return

    Product.update_render_for_id(product_id, rendered_product)


def handle_bot_result(result: dict[str, Any]) -> None:
    bot_result = result.get("result")
    if not isinstance(bot_result, dict):
        logger.error("Invalid bot task result payload")
        return

    error_message = bot_result.get("error") or bot_result.get("message")
    if error_message:
        logger.error(error_message)
        return

    bot_type = result.get("bot_type", "")
    if bot_type in TAGGING_BOTS:
        NewsItemTagService.set_found_bot_tags(result, change_by_bot=True)

    NewsItemTagService.set_bot_execution_attribute(result)

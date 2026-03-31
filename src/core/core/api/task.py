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

        task_id = data.get("task_id")
        result = data.get("result")
        status = data.get("status")
        task = data.get("task", "")

        logger.debug(f"Received task result with id {task_id} and status {status}")

        if status == "SUCCESS" and result:
            handle_task_specific_result(task_id, result, status, task)
        TaskModel.add_or_update({"id": task_id, "result": serialize_result(result, task), "status": status, "task": task})
        return {"status": status}, 200


def initialize(app: Flask):
    task_bp = Blueprint("tasks", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/tasks")

    task_bp.add_url_rule("", view_func=Task.as_view("tasks"))
    task_bp.add_url_rule("/<string:task_id>", view_func=Task.as_view("task"))
    app.register_blueprint(task_bp)


def serialize_result(result: dict | str | None = None, task_name: str | None = None):
    if result is None:
        return None

    if isinstance(result, str):
        return result
    if task_name == "connector_task":
        return result
    if "exc_message" in result:
        if isinstance(result["exc_message"], (list, tuple)):
            return " ".join(map(str, result["exc_message"]))
        return result["exc_message"]

    return result["message"] if "message" in result else result


def _get_dict_result(result: dict[str, Any] | str, task_name: str) -> dict[str, Any] | None:
    if isinstance(result, dict):
        return result

    logger.error(f"Invalid {task_name} task result type: {type(result)}")
    return None


def handle_task_specific_result(task_id: str, result: dict | str, _status: str, task_name: str | None = None):
    task_name = task_name or ""

    if task_id.startswith("gather_word_list") or task_name == "gather_word_list":
        if not (result_dict := _get_dict_result(result, "gather_word_list")):
            return

        content = result_dict.get("content")
        content_type = result_dict.get("content_type")
        word_list_id = result_dict.get("word_list_id")
        if not isinstance(content, str) or not isinstance(content_type, str) or not isinstance(word_list_id, int):
            logger.error("Invalid gather_word_list task result payload")
            return

        WordList.update_word_list(content=content, content_type=content_type, word_list_id=word_list_id)
    elif task_id.startswith("cleanup_token_blacklist") or task_name == "cleanup_token_blacklist":
        TokenBlacklist.delete_older(datetime.now() - Config.JWT_ACCESS_TOKEN_EXPIRES)
    elif task_id.startswith("presenter_task") or task_name == "presenter_task":
        if not (result_dict := _get_dict_result(result, "presenter_task")):
            return

        rendered_product = result_dict.get("render_result")
        product_id = result_dict.get("product_id")
        if not isinstance(product_id, str) or not isinstance(rendered_product, str):
            logger.error(f"Product {product_id} not found or no render result")
            return

        Product.update_render_for_id(product_id, rendered_product)
    elif task_id.startswith("collect_") or task_name == "collector_task":
        logger.info(f"Collector task {task_id} completed with result: {result}")
    elif task_id.startswith("bot") or task_name == "bot_task":
        if not (result_dict := _get_dict_result(result, "bot_task")):
            return

        bot_result = result_dict.get("result")
        if not isinstance(bot_result, dict):
            logger.error("Invalid bot task result payload")
            return

        if bot_result.get("error") or bot_result.get("message"):
            logger.error(bot_result.get("error") or bot_result.get("message"))
            return

        bot_type = result_dict.get("bot_type", "")
        tagging_bots = ["WORDLIST_BOT", "IOC_BOT", "NLP_BOT", "TAGGING_BOT"]
        if bot_type in tagging_bots:
            NewsItemTagService.set_found_bot_tags(result_dict, change_by_bot=True)

        NewsItemTagService.set_bot_execution_attribute(result_dict)
    elif task_name == "connector_task":
        handle_misp_connector_result(result)

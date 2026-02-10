# type: ignore
from datetime import datetime

from flask import Blueprint, Flask, request
from flask.views import MethodView

from core.config import Config
from core.log import logger
from core.managers.auth_manager import api_key_required
from core.model.product import Product
from core.model.task import Task as TaskModel
from core.model.token_blacklist import TokenBlacklist
from core.model.word_list import WordList
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
        TaskModel.add_or_update({"id": task_id, "result": serialize_result(result), "status": status, "task": task})
        return {"status": status}, 200


def initialize(app: Flask):
    task_bp = Blueprint("tasks", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/tasks")

    task_bp.add_url_rule("", view_func=Task.as_view("tasks"))
    task_bp.add_url_rule("/<string:task_id>", view_func=Task.as_view("task"))
    app.register_blueprint(task_bp)


def serialize_result(result: dict | str | None = None):
    if result is None:
        return None

    if isinstance(result, str):
        return result
    if "exc_message" in result:
        if isinstance(result["exc_message"], (list, tuple)):
            return " ".join(map(str, result["exc_message"]))
        return result["exc_message"]

    return result["message"] if "message" in result else result


def handle_task_specific_result(task_id: str, result: dict | str, status: str, task_name: str | None = None):
    task_identifier = task_name or task_id

    if task_identifier.startswith("gather_word_list"):
        WordList.update_word_list(**result)
    elif task_identifier.startswith("cleanup_token_blacklist"):
        TokenBlacklist.delete_older(datetime.now() - Config.JWT_ACCESS_TOKEN_EXPIRES)
    elif task_identifier.startswith("presenter_task"):
        rendered_product = result.get("render_result")
        product_id = result.get("product_id")
        if not product_id or not rendered_product:
            logger.error(f"Product {product_id} not found or no render result")
        else:
            Product.update_render_for_id(product_id, rendered_product)
    elif task_identifier.startswith("collect_"):
        logger.info(f"Collector task {task_id} completed with result: {result}")
    # TODO: check, when falsy values make sense as results. e.g. IOC bot may make sense, but summary bot may want to be executed again and again and not save the bot_type attribute
    elif task_id.startswith("bot"):
        result_data = result.get("result")
        if isinstance(result_data, dict) and (result_data.get("error") or result_data.get("message")):
            logger.error((result_data.get("error") or result_data.get("message")))
            return
        bot_type = result.get("bot_type", "")
        tagging_bots = ["WORDLIST_BOT", "IOC_BOT", "NLP_BOT", "TAGGING_BOT"]
        if bot_type in tagging_bots:
            NewsItemTagService.set_found_bot_tags(result, change_by_bot=True)

        NewsItemTagService.set_bot_execution_attribute(result)

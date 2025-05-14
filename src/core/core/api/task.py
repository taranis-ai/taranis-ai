from flask import request, Flask, Blueprint
from flask.views import MethodView
from datetime import datetime

from core.managers.auth_manager import api_key_required
from core.model.task import Task as TaskModel
from core.log import logger
from core.model.word_list import WordList
from core.model.token_blacklist import TokenBlacklist
from core.model.product import Product
from core.config import Config


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

        logger.debug(f"Received task result with id {task_id} and status {status} with result {result}")

        if not result or "error" in result or status == "FAILURE":
            TaskModel.add_or_update({"id": task_id, "result": serialize_result(result), "status": status})
            return {"status": status}, 400

        if handle_task_specific_result(task_id, result):
            return {"status": status}, 201

        TaskModel.add_or_update({"id": task_id, "result": serialize_result(result), "status": status})
        return {"status": status}, 201


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

    if "message" in result:
        return result["message"]
    return result


def handle_task_specific_result(task_id: str, result: dict) -> bool:
    if task_id.startswith("gather_word_list"):
        WordList.update_word_list(**result)
    elif task_id.startswith("cleanup_token_blacklist"):
        TokenBlacklist.delete_older(datetime.now() - Config.JWT_ACCESS_TOKEN_EXPIRES)
    elif task_id.startswith("presenter_task"):
        rendered_product = result.get("render_result")
        product_id = result.get("product_id")
        if not product_id or not rendered_product:
            logger.error(f"Product {product_id} not found or no render result")
            return False
        Product.update_render_for_id(product_id, rendered_product)
    else:
        return False
    return True

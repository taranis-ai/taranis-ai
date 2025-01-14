from flask import request, Flask, Blueprint
from flask.views import MethodView
from datetime import datetime, timedelta

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

        if not result or not status or "error" in result:
            logger.error(f"{task_id=} - {result=} - {status=}")

            # failed presenter_tasks are saved in the tasks table
            if result and task_id.startswith("presenter_task"):
                task_data = {"id": result.get("product_id"), "result": result.get("message"), "status": status}
                TaskModel.add_or_update(task_data)
            return {"status": "error"}, 400

        if task_id.startswith("gather_word_list"):
            WordList.update_word_list(**result)
        elif task_id.startswith("cleanup_token_blacklist"):
            TokenBlacklist.delete_older(datetime.now() - timedelta(days=1))
        elif task_id.startswith("presenter_task"):
            Product.update_render_for_id(result.get("product_id"), result.get("render_result", "").encode("utf-8"))
        else:
            task_data = {"id": task_id, "result": result, "status": status}
            TaskModel.add_or_update(task_data)
        return {"status": status}, 201


def initialize(app: Flask):
    task_bp = Blueprint("tasks", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/tasks")

    task_bp.add_url_rule("", view_func=Task.as_view("tasks"))
    task_bp.add_url_rule("/<string:task_id>", view_func=Task.as_view("task"))
    app.register_blueprint(task_bp)

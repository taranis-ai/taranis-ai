from flask import request, Flask
from flask.views import MethodView
from datetime import datetime, timedelta

from core.managers.auth_manager import api_key_required
from core.model.task import Task as TaskModel
from core.log import logger
from core.model.word_list import WordList
from core.model.token_blacklist import TokenBlacklist


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
            return {"status": "error"}, 400

        if task_id.startswith("gather_word_list"):
            WordList.update_word_list(**result)
        elif task_id.startswith("cleanup_token_blacklist"):
            TokenBlacklist.delete_older(datetime.now() - timedelta(days=1))
        elif task_id.startswith("presenter_task"):
            task_data = {"id": result.get("product_id"), "result": result.get("message"), "status": status}
            TaskModel.add_or_update(task_data)
        else:
            task_data = {"id": task_id, "result": result, "status": status}
            TaskModel.add_or_update(task_data)
        return {"status": status}, 201


def initialize(app: Flask):
    app.add_url_rule("/api/tasks", view_func=Task.as_view("tasks"))
    app.add_url_rule("/api/tasks/", view_func=Task.as_view("tasks_"))
    app.add_url_rule("/api/tasks/<string:task_id>", view_func=Task.as_view("task"))

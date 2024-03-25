from flask_restx import Resource, Namespace, Api
from flask import request

from core.managers.auth_manager import api_key_required
from core.model.task import Task as TaskModel


class Task(Resource):
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

        task_data = {"id": data.get("task_id"), "result": data.get("result"), "status": data.get("status")}
        TaskModel.add_or_update(task_data)
        return {"status": "success"}, 201


def initialize(api: Api):
    namespace = Namespace("tasks", description="Celery Task API")

    namespace.add_resource(Task, "/", "/<string:task_id>")
    api.add_namespace(namespace, path="/tasks")

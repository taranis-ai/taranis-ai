from celery.backends.base import BaseBackend
from worker.core_api import CoreApi


class HTTPBackend(BaseBackend):
    def __init__(self, app=None, **kwargs):
        super().__init__(app, **kwargs)
        self.core_api = CoreApi()

    def store_result(self, task_id, result, status, traceback=None, request=None, **kwargs):
        data = {
            "task_id": task_id,
            "status": status,
            "result": self.encode_result(result, status),
            "traceback": traceback,
        }
        self.core_api.store_task_result(data)

    def _get_task_meta_for(self, task_id, default=None):
        response = self.core_api.get_task(task_id)
        if response.status_code != 200:
            return {"status": "PENDING", "result": default}
        data = response.json()
        return self.decode_result(data["result"])

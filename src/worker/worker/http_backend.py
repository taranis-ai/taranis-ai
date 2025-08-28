from celery.backends.base import BaseBackend
from celery.app.task import Context

from worker.core_api import CoreApi
from worker.log import logger


class HTTPBackend(BaseBackend):
    def __init__(self, app=None, **kwargs):
        super().__init__(app, **kwargs)
        self.core_api = CoreApi()

    def store_result(
        self,
        task_id: str,
        result: dict | str | Exception | None,
        state: str,
        traceback: str | None = None,
        request: Context | None = None,
        **kwargs,
    ):
        logger.info(f"Storing result for task {task_id}: {self._serialize_context(request)}")
        data = {
            "task_id": task_id,
            "status": state,
            "result": self.encode_result(result, state),
            "traceback": traceback,
            "task": self._serialize_context(request),
        }
        self.core_api.store_task_result(data)

    def _get_task_meta_for(self, task_id, default=None):
        response = self.core_api.get_task(task_id)
        if response.status_code != 200:
            return {"status": "PENDING", "result": default}
        data = response.json()
        return self.decode_result(data["result"])

    def _serialize_context(self, request: Context | None) -> dict | None:
        if not request:
            return None
        try:
            return getattr(request, "task", None)
        except Exception:
            return None

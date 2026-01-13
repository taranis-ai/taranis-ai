import requests
from flask import current_app


class CoreApiClient:
    def __init__(self):
        self.base_url = current_app.config["CORE_API_BASE_URL"]
        self.api_key = current_app.config["API_KEY"]

    def get_task(self, task_id: str):
        return requests.get(
            f"{self.base_url}/api/tasks/{task_id}",
            headers={"Authorization": f"Bearer {self.api_key.get_secret_value()}"},
            timeout=5,
        )

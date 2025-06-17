import requests
from datetime import datetime

from core.config import Config
from core.log import logger


class SSEManager:
    def __init__(self):
        self.report_item_locks: dict = {}
        self.sse_url = Config.SSE_URL
        self.api_key = Config.API_KEY.get_secret_value()
        self.headers = self.get_headers()
        self.timeout = 60
        self.broker_error = 0

    def get_headers(self) -> dict:
        return {"X-API-KEY": self.api_key, "Content-type": "application/json"}

    def publish(self, json_data) -> bool:
        if self.broker_error > 3 or Config.DISABLE_SSE:
            return False
        try:
            response = requests.post(url=self.sse_url, headers=self.headers, json=json_data, timeout=self.timeout)
            if not response.ok:
                logger.debug(f"Failed to publish to SSE: {response.text}")
                self.broker_error += 1

            logger.debug(f"Publishing to SSE: {json_data}")
            return response.ok
        except requests.exceptions.RequestException:
            self.broker_error += 1
            return False

    def connected(self):
        self.publish({"data": "Connected", "event": "connected"})

    def news_items_updated(self):
        self.publish({"data": "News Item Updated", "event": "news-items-updated"})

    def report_item_updated(self, data):
        self.publish({"data": data, "event": "report-item-updated"})

    def product_rendered(self, data):
        self.publish({"data": data, "event": "product-rendered"})

    def to_report_item_json(self, report_item_id: int):
        if report_item_id not in self.report_item_locks.keys():
            return {"report_item_id": report_item_id, "locked": False}
        return {
            "report_item_id": report_item_id,
            "locked": True,
            "lock_time": self.report_item_locks[report_item_id]["lock_time"].astimezone().isoformat(timespec="seconds"),
        }

    def report_item_lock(self, report_item_id: int, user_id):
        if report_item_id in self.report_item_locks:
            if self.report_item_locks[report_item_id]["user_id"] == user_id:
                self.report_item_locks[report_item_id]["lock_time"] = datetime.now()
            return self.to_report_item_json(report_item_id), 200
        self.report_item_locks[report_item_id] = {"user_id": user_id, "lock_time": datetime.now()}
        self.publish(
            {
                "data": report_item_id,
                "event": "report-item-locked",
            }
        )
        return self.to_report_item_json(report_item_id), 200
        # schedule.every(1).minute.do(self.schedule_unlock_report_item, report_item_id, user_id)

    def report_item_unlock(self, report_item_id: int, user_id):
        if report_item_id not in self.report_item_locks.keys():
            return self.to_report_item_json(report_item_id), 200

        del self.report_item_locks[report_item_id]

        self.publish(
            {
                "data": report_item_id,
                "event": "report-item-unlocked",
            }
        )
        return self.to_report_item_json(report_item_id), 200

    # def schedule_unlock_report_item(self, report_item_id: int, user_id, time_to_unlock: datetime):
    #     if report_item_id not in self.report_item_locks:
    #         return schedule.CancelJob

    #     if self.report_item_locks[report_item_id]["user_id"] != user_id:
    #         return schedule.CancelJob

    #     if self.report_item_locks[report_item_id]["lock_time"] > time_to_unlock:
    #         return

    #     self.report_item_unlock(report_item_id, user_id)
    #     return schedule.CancelJob


sse_manager = SSEManager()

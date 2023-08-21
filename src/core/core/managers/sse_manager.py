from datetime import datetime
from core.managers.sse import SSE
from flask import jsonify


class SSEManager:
    def __init__(self):
        self.report_item_locks: dict = {}
        self.sse: SSE = SSE()

    def news_items_updated(self):
        self.sse.publish({}, event="news-items-updated")

    def report_items_updated(self):
        self.sse.publish({}, event="report-items-updated")

    def report_item_updated(self, data):
        self.sse.publish(data, event="report-item-updated")

    def to_json(self, report_item_id: int):
        return {}
        if report_item_id not in self.report_item_locks.keys():
            return jsonify({"report_item_id": report_item_id, "locked": False})
        return jsonify(
            {"report_item_id": report_item_id, "locked": True, "lock_time": self.report_item_locks[report_item_id]["lock_time"].isoformat()}
        )

    def report_item_lock(self, report_item_id: int, user_id):
        if report_item_id in self.report_item_locks:
            if self.report_item_locks[report_item_id]["user_id"] == user_id:
                self.report_item_locks[report_item_id]["lock_time"] = datetime.now()
            return self.to_json(report_item_id), 200
        self.report_item_locks[report_item_id] = {"user_id": user_id, "lock_time": datetime.now()}
        self.sse.publish(
            {
                "report_item_id": report_item_id,
                "user_id": user_id,
            },
            event="report-item-locked",
        )
        return self.to_json(report_item_id), 200
        # schedule.every(1).minute.do(self.schedule_unlock_report_item, report_item_id, user_id)

    def report_item_unlock(self, report_item_id: int, user_id):
        if report_item_id not in self.report_item_locks.keys():
            return self.to_json(report_item_id), 200

        del self.report_item_locks[report_item_id]

        self.sse.publish(
            {
                "report_item_id": report_item_id,
                "user_id": user_id,
            },
            event="report-item-unlocked",
        )
        return self.to_json(report_item_id), 200

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

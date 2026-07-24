from datetime import datetime

from core.managers.realtime_publisher import realtime_publisher


class ReportItemLockService:
    def __init__(self):
        self.report_item_locks: dict = {}

    def to_report_item_json(self, report_item_id: str):
        if report_item_id not in self.report_item_locks:
            return {"report_item_id": report_item_id, "locked": False}
        return {
            "report_item_id": report_item_id,
            "locked": True,
            "lock_time": self.report_item_locks[report_item_id]["lock_time"].astimezone().isoformat(timespec="seconds"),
        }

    def lock(self, report_item_id: str, user_id: str, organization_id: str | None):
        if report_item_id in self.report_item_locks:
            if self.report_item_locks[report_item_id]["user_id"] == user_id:
                self.report_item_locks[report_item_id]["lock_time"] = datetime.now()
            return self.to_report_item_json(report_item_id), 200

        self.report_item_locks[report_item_id] = {"user_id": user_id, "lock_time": datetime.now()}
        if organization_id:
            realtime_publisher.report_lock_changed(report_item_id, organization_id)
        return self.to_report_item_json(report_item_id), 200

    def unlock(self, report_item_id: str, organization_id: str | None):
        if report_item_id not in self.report_item_locks:
            return self.to_report_item_json(report_item_id), 200

        del self.report_item_locks[report_item_id]
        if organization_id:
            realtime_publisher.report_lock_changed(report_item_id, organization_id)
        return self.to_report_item_json(report_item_id), 200


report_item_lock_service = ReportItemLockService()

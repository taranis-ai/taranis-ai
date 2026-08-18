from datetime import UTC, datetime
from threading import Lock

from core.managers.realtime_publisher import realtime_publisher


class ReportItemLockService:
    def __init__(self) -> None:
        self.report_item_locks: dict = {}
        self._lock = Lock()

    def _to_report_item_json(self, report_item_id: str) -> dict[str, str | bool]:
        if report_item_id not in self.report_item_locks:
            return {"report_item_id": report_item_id, "locked": False}
        return {
            "report_item_id": report_item_id,
            "locked": True,
            "lock_time": self.report_item_locks[report_item_id]["lock_time"].astimezone().isoformat(timespec="seconds"),
        }

    def to_report_item_json(self, report_item_id: str) -> dict[str, str | bool]:
        with self._lock:
            return self._to_report_item_json(report_item_id)

    def lock(self, report_item_id: str, user_id: str, organization_id: str | None) -> tuple[dict[str, str | bool], int]:
        with self._lock:
            if report_item_id in self.report_item_locks:
                if self.report_item_locks[report_item_id]["user_id"] == user_id:
                    self.report_item_locks[report_item_id]["lock_time"] = datetime.now(UTC)
                return self._to_report_item_json(report_item_id), 200

            self.report_item_locks[report_item_id] = {"user_id": user_id, "lock_time": datetime.now(UTC)}
            response = self._to_report_item_json(report_item_id)
        if organization_id:
            realtime_publisher.report_lock_changed(report_item_id, organization_id)
        return response, 200

    def unlock(self, report_item_id: str, organization_id: str | None) -> tuple[dict[str, str | bool], int]:
        with self._lock:
            if report_item_id not in self.report_item_locks:
                return self._to_report_item_json(report_item_id), 200

            del self.report_item_locks[report_item_id]
            response = self._to_report_item_json(report_item_id)
        if organization_id:
            realtime_publisher.report_lock_changed(report_item_id, organization_id)
        return response, 200


report_item_lock_service = ReportItemLockService()

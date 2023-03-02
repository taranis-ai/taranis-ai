from datetime import datetime
import schedule
from core.model.remote import RemoteAccess
from core.managers.sse import SSE


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

    def remote_access_disconnect(self, data):
        self.sse.publish(data, event="remote_access_disconnect")

    def remote_access_news_items_updated(self, osint_source_ids):
        remote_access_event_ids = RemoteAccess.get_relevant_for_news_items(osint_source_ids)
        data = str(remote_access_event_ids).join(",")
        self.sse.publish(
            data,
            event="remote_access_news_items_updated",
        )

    def remote_access_report_items_updated(self, report_item_type_id):
        remote_access_event_ids = RemoteAccess.get_relevant_for_report_item(report_item_type_id)
        data = str(remote_access_event_ids).join(",")
        self.sse.publish(
            data,
            event="remote_access_report_items_updated",
        )

    def report_item_lock(self, report_item_id: int, user_id):
        if report_item_id in self.report_item_locks:
            if self.report_item_locks[report_item_id]["user_id"] == user_id:
                self.report_item_locks[report_item_id]["lock_time"] = datetime.now()
            return
        self.report_item_locks[report_item_id] = {"user_id": user_id, "lock_time": datetime.now()}
        self.sse.publish(
            {
                "report_item_id": report_item_id,
                "user_id": user_id,
            },
            event="report-item-locked",
        )
        schedule.every(1).minute.do(self.schedule_unlock_report_item, report_item_id, user_id)

    def report_item_unlock(self, report_item_id: int, user_id):
        del self.report_item_locks[report_item_id]

        self.sse.publish(
            {
                "report_item_id": report_item_id,
                "user_id": user_id,
            },
            event="report-item-unlocked",
        )

    def schedule_unlock_report_item(self, report_item_id: int, user_id, time_to_unlock: datetime):
        if report_item_id not in self.report_item_locks:
            return schedule.CancelJob

        if self.report_item_locks[report_item_id]["user_id"] != user_id:
            return schedule.CancelJob

        if self.report_item_locks[report_item_id]["lock_time"] > time_to_unlock:
            return

        self.report_item_unlock(report_item_id, user_id)
        return schedule.CancelJob


sse_manager = SSEManager()

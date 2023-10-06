from typing import Any
from datetime import datetime

from core.managers.db_manager import db
from core.managers.log_manager import logger
from core.model.base_model import BaseModel


class ScheduleEntry(BaseModel):
    id = db.Column(db.String, primary_key=True)
    task = db.Column(db.String)
    schedule = db.Column(db.String)
    args = db.Column(db.String)
    last_run_at = db.Column(db.DateTime)
    next_run_time = db.Column(db.DateTime)
    total_run_count = db.Column(db.Integer)

    def __init__(self, id, task, schedule, args):
        self.id = id
        self.task = task
        self.schedule = schedule
        self.args = args
        self.total_run_count = 0

    def update(self, data):
        update_data = self.from_dict(data)
        self.schedule = update_data.schedule
        self.args = update_data.args
        db.session.commit()

    @classmethod
    def add_or_update(cls, entry_data):
        if entry := cls.get(entry_data["id"]):
            entry.update(entry_data)
            db.session.commit()
            return entry, 200
        entry = cls.from_dict(entry_data)
        db.session.add(entry)
        db.session.commit()
        return entry, 200

    @classmethod
    def sync(cls, entries: list["ScheduleEntry"]):
        for entry in entries:
            if existing_entry := cls.get(entry.id):
                existing_entry.schedule = entry.schedule
                existing_entry.args = entry.args
                existing_entry.last_run_at = entry.last_run_at
                existing_entry.total_run_count = entry.total_run_count
            else:
                db.session.add(entry)
            db.session.commit()
        return "Schedule updated", 200

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScheduleEntry":
        data["args"] = ",".join(data.get("args", []))
        return ScheduleEntry(**data)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["next_run_time"] = self.next_run_time.isoformat() if self.next_run_time else None
        data["last_run_at"] = self.last_run_at.isoformat() if self.last_run_at else None
        return data

    @classmethod
    def update_next_run_time(cls, next_run_times: dict):
        for entry_id, runtime in next_run_times.items():
            if entry := cls.get(entry_id):
                if db.session.get_bind().dialect.name == "sqlite":
                    entry.next_run_time = datetime.fromisoformat(runtime)
                else:
                    entry.next_run_time = runtime
                db.session.commit()
            else:
                logger.error(f"Schedule entry {entry_id} not found")
        return {"message": "Next run times updated"}, 200

    def to_worker_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.pop("next_run_time")
        data["name"] = data.pop("id")
        data["args"] = data.get("args", "").split(",")
        if schedule := data.get("schedule"):
            if schedule == "hourly":
                data["schedule"] = 60 * 60
            elif schedule == "daily":
                data["schedule"] = 1440 * 60
            elif schedule == "weekly":
                data["schedule"] = 10080 * 60
            elif isinstance(schedule, int):
                data["schedule"] = schedule * 60
            elif isinstance(schedule, str) and schedule.isdigit():
                data["schedule"] = int(schedule) * 60
            else:
                data["schedule"] = 600 * 60
        data["last_run_at"] = self.last_run_at.isoformat() if self.last_run_at else None
        return data

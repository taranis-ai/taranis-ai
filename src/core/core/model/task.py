import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import case, func
from sqlalchemy.orm import Mapped

from core.managers.db_manager import db
from core.model.base_model import BaseModel


class Task(BaseModel):
    __tablename__ = "task"

    id: Mapped[str] = db.Column(db.String, primary_key=True)
    task: Mapped[str] = db.Column(db.String, nullable=True)
    result: Mapped[str] = db.Column(db.String, nullable=True)
    status: Mapped[str] = db.Column(db.String, nullable=True)
    last_run: Mapped[datetime] = db.Column(db.DateTime, nullable=True)
    last_success: Mapped[datetime] = db.Column(db.DateTime, nullable=True)

    def __init__(self, result=None, status=None, id=None, task=None):
        if id:
            self.id = id
        if status:
            self.status = status
        if task:
            self.task = task
        self.result = json.dumps(result) if result else ""
        if status == "SUCCESS":
            self.last_success = datetime.now(timezone.utc)
        self.last_run = datetime.now(timezone.utc)

    @classmethod
    def add_or_update(cls, entry_data):
        if entry := cls.get(entry_data["id"]):
            entry.result = json.dumps(entry_data["result"]) if entry_data["result"] else ""
            entry.status = entry_data.get("status")
            entry.task = entry_data.get("task", entry.task)
            if entry.status == "SUCCESS":
                entry.last_success = datetime.now(timezone.utc)
            entry.last_run = datetime.now(timezone.utc)
            db.session.commit()
            return entry.to_dict(), 200
        new_entry = cls.add(entry_data)
        return new_entry.to_dict(), 201

    def to_dict(self):
        result = json.loads(self.result) if self.result else None
        return {
            "id": self.id,
            "result": result,
            "task": self.task,
            "status": self.status,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
        }

    @classmethod
    def get_failed(cls, task_id: str) -> "Task | None":
        return db.session.execute(db.select(cls).where(cls.id == task_id).where(cls.status == "FAILURE")).scalar()

    @classmethod
    def get_successful(cls, task_id: str) -> "Task | None":
        return db.session.execute(db.select(cls).where(cls.id == task_id).where(cls.status == "SUCCESS")).scalar()

    @classmethod
    def get_failed_by_task(cls, task_type: str) -> int:
        """returns the number of tasks failed based on the task type which is determined by task"""
        stmt = db.select(func.count()).select_from(cls).where(cls.task.like(f"%{task_type}%")).where(cls.status == "FAILURE")
        return db.session.execute(stmt).scalar_one()

    @classmethod
    def get_status_counts_by_task(cls, include_timestamps: bool = False) -> dict[str, dict[str, Any]]:
        """Return per-task execution stats grouped by task identifier."""

        columns = [
            cls.task.label("task_type"),
            func.count(case((cls.status == "FAILURE", 1))).label("failures"),
            func.count(case((cls.status == "SUCCESS", 1))).label("successes"),
        ]

        if include_timestamps:
            columns.append(func.max(cls.last_run).label("last_run"))
            columns.append(func.max(cls.last_success).label("last_success"))

        stmt = db.select(*columns).where(cls.task.is_not(None)).group_by(cls.task)

        results = db.session.execute(stmt).all()

        data: dict[str, dict[str, Any]] = {}
        for row in results:
            failures = row.failures or 0
            successes = row.successes or 0
            total = failures + successes
            success_pct = int((successes * 100) / total) if total else 0
            entry: dict[str, Any] = {
                "failures": failures,
                "successes": successes,
                "success_pct": success_pct,
                "total": total,
            }

            if include_timestamps:
                entry["last_run"] = row.last_run
                entry["last_success"] = row.last_success

            data[row.task_type] = entry
        return data

    @staticmethod
    def _build_task_status_badge(stats: dict[str, Any]) -> dict[str, str]:
        successes = int(stats.get("successes") or 0)
        failures = int(stats.get("failures") or 0)
        total_runs = int(stats.get("total") or successes + failures)
        success_pct = int(stats.get("success_pct") or 0)

        if total_runs == 0:
            return {"variant": "ghost", "label": "No Runs"}
        if failures == 0:
            return {"variant": "success", "label": "All Success"}
        if failures == 1 and total_runs == 1:
            return {"variant": "warning", "label": "First Failure"}
        if success_pct >= 80:
            return {"variant": "warning", "label": "Mostly Success"}
        if failures <= 2:
            return {"variant": "warning", "label": "Some Failures"}
        return {"variant": "error", "label": "Many Failures"}

    @classmethod
    def _format_task_stats(cls, raw_stats: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        formatted: dict[str, dict[str, Any]] = {}
        for task_name, stats in raw_stats.items():
            formatted_stats = stats.copy()

            formatted_stats["last_run_display"] = stats.get("last_run")
            formatted_stats["last_success_display"] = stats.get("last_success")
            formatted_stats["status_badge"] = cls._build_task_status_badge(formatted_stats)
            formatted[task_name] = formatted_stats
        return formatted

    @classmethod
    def get_task_statistics(cls) -> dict[str, Any]:
        """Return per-task stats along with overall totals."""

        raw_task_stats = cls.get_status_counts_by_task(include_timestamps=True)
        task_stats = cls._format_task_stats(raw_task_stats)
        total_successes = sum(stat.get("successes", 0) for stat in raw_task_stats.values())
        total_failures = sum(stat.get("failures", 0) for stat in raw_task_stats.values())
        overall_total = total_successes + total_failures
        overall_success_rate = int((total_successes * 100) / overall_total) if overall_total else 0

        return {
            "task_stats": task_stats,
            "totals": {
                "successes": total_successes,
                "failures": total_failures,
                "overall_success_rate": overall_success_rate,
            },
        }

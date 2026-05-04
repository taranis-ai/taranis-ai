import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Mapped

from core.managers.db_manager import db
from core.model.base_model import BaseModel


class Task(BaseModel):
    __tablename__ = "task"

    SUCCESS_STATUSES = {"SUCCESS", "NOT_MODIFIED"}
    FAILURE_STATUSES = {"FAILURE"}

    id: Mapped[str] = db.Column(db.String, primary_key=True)
    task: Mapped[str] = db.Column(db.String, nullable=True)
    worker_id: Mapped[str] = db.Column(db.String, nullable=True)
    worker_type: Mapped[str] = db.Column(db.String, nullable=True)
    result: Mapped[str] = db.Column(db.String, nullable=True)
    status: Mapped[str] = db.Column(db.String, nullable=True)
    last_run: Mapped[datetime] = db.Column(db.DateTime, nullable=True)
    last_success: Mapped[datetime] = db.Column(db.DateTime, nullable=True)

    def __init__(self, result=None, status=None, id=None, task=None, worker_id=None, worker_type=None):
        if id:
            self.id = id
        if status:
            self.status = status
        if task:
            self.task = task
        if worker_id is not None:
            self.worker_id = worker_id
        if worker_type is not None:
            self.worker_type = worker_type
        self.result = json.dumps(result) if result is not None else ""
        if status in self.SUCCESS_STATUSES:
            self.last_success = datetime.now(timezone.utc)
        self.last_run = datetime.now(timezone.utc)

    @classmethod
    def add_or_update(cls, entry_data):
        if entry := cls.get(entry_data["id"]):
            entry.result = json.dumps(entry_data["result"]) if entry_data["result"] is not None else ""
            entry.status = entry_data.get("status")
            entry.task = entry_data.get("task", entry.task)
            entry.worker_id = entry_data.get("worker_id", entry.worker_id)
            entry.worker_type = entry_data.get("worker_type", entry.worker_type)
            if entry.status in cls.SUCCESS_STATUSES:
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
            "worker_id": self.worker_id,
            "worker_type": self.worker_type,
            "status": self.status,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
        }

    @classmethod
    def get_failed(cls, task_id: str) -> "Task | None":
        return db.session.execute(db.select(cls).where(cls.id == task_id).where(cls.status == "FAILURE")).scalar()

    @classmethod
    def get_successful(cls, task_id: str) -> "Task | None":
        return db.session.execute(db.select(cls).where(cls.id == task_id).where(cls.status.in_(cls.SUCCESS_STATUSES))).scalar()

    @classmethod
    def get_latest_matching(
        cls,
        *,
        exact_ids: set[str] | None = None,
        prefixes: list[str] | None = None,
        task_name: str | None = None,
    ) -> "Task | None":
        conditions = []

        exact_ids = {task_id for task_id in (exact_ids or set()) if task_id}
        prefixes = [prefix for prefix in (prefixes or []) if prefix]

        if exact_ids:
            conditions.append(cls.id.in_(exact_ids))
        conditions.extend(cls.id.like(f"{prefix}%") for prefix in prefixes)

        if not conditions:
            return None

        stmt = db.select(cls).where(or_(*conditions))
        if task_name is not None:
            stmt = stmt.where(cls.task == task_name)

        stmt = stmt.order_by(cls.last_run.desc(), cls.last_success.desc(), cls.id.desc()).limit(1)
        return db.session.execute(stmt).scalars().first()

    @classmethod
    def get_failed_by_task(cls, task_type: str) -> int:
        """returns the number of tasks failed based on the task type which is determined by task"""
        stmt = db.select(func.count()).select_from(cls).where(cls.task.like(f"%{task_type}%")).where(cls.status == "FAILURE")
        return db.session.execute(stmt).scalar_one()

    @classmethod
    def get_status_counts_by_task(
        cls,
        include_timestamps: bool = False,
    ) -> dict[str, dict[str, Any]]:
        """Return per-task execution stats grouped by worker type.

        Counts are based on the latest persisted result per worker identity so repeated
        runs of the same bot or OSINT source do not inflate the totals.
        """

        task_label = func.coalesce(cls.worker_type, cls.task)
        worker_key = func.coalesce(cls.worker_id, cls.id)
        group_filter = or_(cls.worker_type.is_not(None), cls.task.is_not(None))

        stmt = (
            db.select(
                task_label.label("task_type"),
                worker_key.label("worker_key"),
                cls.status.label("status"),
                cls.worker_type.label("worker_type"),
                cls.worker_id.label("worker_id"),
                cls.last_run.label("last_run"),
                cls.last_success.label("last_success"),
            )
            .where(group_filter)
            .order_by(
                task_label,
                worker_key,
                cls.last_run.desc(),
                cls.last_success.desc(),
                cls.id.desc(),
            )
        )

        results = db.session.execute(stmt).all()

        data: dict[str, dict[str, Any]] = {}
        seen_workers: dict[str, set[str]] = {}

        for row in results:
            task_type = row.task_type
            worker_key_value = row.worker_key
            if task_type not in data:
                entry: dict[str, Any] = {
                    "failures": 0,
                    "successes": 0,
                    "success_pct": 0,
                    "total": 0,
                    "worker_type": row.worker_type or task_type,
                    "worker_id": row.worker_id,
                }
                if include_timestamps:
                    entry["last_run"] = row.last_run
                    entry["last_success"] = row.last_success
                data[task_type] = entry
                seen_workers[task_type] = set()

            entry = data[task_type]
            if include_timestamps:
                current_last_run = entry.get("last_run")
                if row.last_run and (current_last_run is None or row.last_run > current_last_run):
                    entry["last_run"] = row.last_run

                current_last_success = entry.get("last_success")
                if row.last_success and (current_last_success is None or row.last_success > current_last_success):
                    entry["last_success"] = row.last_success

            if worker_key_value in seen_workers[task_type]:
                continue

            seen_workers[task_type].add(worker_key_value)
            if len(seen_workers[task_type]) == 1:
                entry["worker_id"] = row.worker_id
            elif entry.get("worker_id") != row.worker_id:
                entry["worker_id"] = None

            if row.status in cls.FAILURE_STATUSES:
                entry["failures"] += 1
            elif row.status in cls.SUCCESS_STATUSES:
                entry["successes"] += 1

        for entry in data.values():
            failures = int(entry.get("failures") or 0)
            successes = int(entry.get("successes") or 0)
            total = failures + successes
            entry["failures"] = failures
            entry["successes"] = successes
            entry["total"] = total
            entry["success_pct"] = int((successes * 100) / total) if total else 0
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

    @staticmethod
    def _serialize_timestamp(value: datetime | str | None) -> str | None:
        if value is None or isinstance(value, str):
            return value
        return value.isoformat()

    @classmethod
    def _format_task_stats(cls, raw_stats: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        formatted: dict[str, dict[str, Any]] = {}
        for task_name, stats in raw_stats.items():
            formatted_stats = stats.copy()
            formatted_stats["last_run"] = cls._serialize_timestamp(stats.get("last_run"))
            formatted_stats["last_success"] = cls._serialize_timestamp(stats.get("last_success"))

            formatted_stats["last_run_display"] = formatted_stats["last_run"]
            formatted_stats["last_success_display"] = formatted_stats["last_success"]
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

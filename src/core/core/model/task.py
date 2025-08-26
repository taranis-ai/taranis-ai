import json
from sqlalchemy.orm import Mapped
from sqlalchemy import func, case
from datetime import datetime, timezone

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
            return entry, 200
        return cls.add(entry_data)

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
    def get_status_counts_by_task(cls) -> dict[str, dict[str, int]]:
        """
        Returns a mapping of task_type -> { 'failures': int, 'successes': int }
        """
        stmt = (
            db.select(
                cls.task.label("task_type"),
                func.count(case((cls.status == "FAILURE", 1))).label("failures"),
                func.count(case((cls.status == "SUCCESS", 1))).label("successes"),
            )
            .where(cls.task.is_not(None))
            .group_by(cls.task)
        )

        results = db.session.execute(stmt).all()

        data = {}
        for row in results:
            total = (row.failures or 0) + (row.successes or 0)
            success_pct = int((row.successes * 100) / total) if total else 0
            data[row.task_type] = {
                "failures": row.failures,
                "successes": row.successes,
                "success_pct": success_pct,
                "total": total,
            }
        return data

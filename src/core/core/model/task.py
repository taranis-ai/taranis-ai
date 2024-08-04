import json
from sqlalchemy.orm import Mapped

from core.managers.db_manager import db
from core.model.base_model import BaseModel


class Task(BaseModel):
    __tablename__ = "task"

    id: Mapped[str] = db.Column(db.String, primary_key=True)
    result: Mapped[str] = db.Column(db.String, nullable=True)
    status: Mapped[str] = db.Column(db.String, nullable=True)

    def __init__(self, result=None, status=None, id=None):
        if id:
            self.id = id
        if status:
            self.status = status
        self.result = json.dumps(result) if result else ""

    @classmethod
    def add_or_update(cls, entry_data):
        if entry := cls.get(entry_data["id"]):
            entry.result = json.dumps(entry_data["result"]) if entry_data["result"] else ""
            entry.status = entry_data.get("status")
            db.session.commit()
            return entry, 200
        return cls.add(entry_data)

    def to_dict(self):
        result = json.loads(self.result) if self.result else None
        return {"id": self.id, "result": result, "status": self.status}

    @classmethod
    def get_failed(cls, task_id: str) -> "Task | None":
        return db.session.execute(db.select(cls).where(cls.id == task_id).where(cls.status == "FAILURE")).scalar()

    @classmethod
    def get_successful(cls, task_id: str) -> "Task | None":
        return db.session.execute(db.select(cls).where(cls.id == task_id).where(cls.status == "SUCCESS")).scalar()

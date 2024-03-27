import json
from core.managers.db_manager import db
from core.model.base_model import BaseModel


class Task(BaseModel):
    id = db.Column(db.String, primary_key=True)
    result = db.Column(db.String, nullable=True)
    status = db.Column(db.String, nullable=True)

    def __init__(self, result=None, status=None, id=None):
        self.id = id
        self.result = json.dumps(result) if result else None
        self.status = status

    @classmethod
    def add_or_update(cls, entry_data):
        if entry := cls.get(entry_data["id"]):
            entry.result = json.dumps(entry_data["result"]) if entry_data["result"] else None
            entry.status = entry_data.get("status")
            db.session.commit()
            return entry, 200
        return cls.add(entry_data)

    def to_dict(self):
        result = json.loads(self.result) if self.result else None
        return {"id": self.id, "result": result, "status": self.status}

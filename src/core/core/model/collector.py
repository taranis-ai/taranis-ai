from sqlalchemy import or_
import uuid
from typing import Any

from core.managers.db_manager import db
from core.model.parameter import Parameter
from core.model.base_model import BaseModel


class Collector(BaseModel):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    type = db.Column(db.String(), nullable=False)
    parameters = db.relationship("Parameter", secondary="collector_parameter", cascade="all")
    sources = db.relationship("OSINTSource", backref="collector")

    def __init__(self, name, description, type, parameters):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type
        self.parameters = parameters

    @classmethod
    def add(cls, data) -> tuple[str, int]:
        if cls.find_by_type(data["type"]):
            return f"Collector with type {data['type']} already exists", 409
        collector = cls.from_dict(data)
        collector.parameters = [Parameter.find_by_key(p) for p in data.pop("parameters") if p is not None]
        db.session.add(collector)
        db.session.commit()
        return f"Collector {collector.name} added", 201

    @classmethod
    def get_first(cls):
        return cls.query.first()

    @classmethod
    def get_type(cls, id) -> "Collector":
        if collector := cls.get(id):
            return collector.type
        else:
            raise ValueError

    @classmethod
    def get_by_filter(cls, search):
        query = cls.query

        if search:
            query = query.filter(
                or_(
                    Collector.name.ilike(f"%{search}%"),
                    Collector.description.ilike(f"%{search}%"),
                )
            )

        return query.order_by(db.asc(Collector.name)).all(), query.count()

    @classmethod
    def find_by_type(cls, type):
        return cls.query.filter_by(type=type).first()

    @classmethod
    def get_all_json(cls, search):
        collectors, count = cls.get_by_filter(search)
        items = [collector.to_dict() for collector in collectors]
        return {"total_count": count, "items": items}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "parameters": [parameter.to_dict() for parameter in self.parameters],
        }


class CollectorParameter(BaseModel):
    collector_id = db.Column(db.String, db.ForeignKey("collector.id", ondelete="CASCADE"), primary_key=True)
    parameter_id = db.Column(db.String, db.ForeignKey("parameter.key", ondelete="CASCADE"), primary_key=True)

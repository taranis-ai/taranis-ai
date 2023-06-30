from dataclasses import dataclass
import uuid
from sqlalchemy import or_, func
from typing import Any

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.parameter import Parameter
from core.managers.log_manager import logger


@dataclass
class Publisher(BaseModel):
    __tablename__ = "publisher"

    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    type = db.Column(db.String(), nullable=False)

    parameters = db.relationship("Parameter", secondary="publisher_parameter")

    node_id = db.Column(db.String, db.ForeignKey("publishers_node.id"))
    node = db.relationship("PublishersNode", back_populates="publishers")

    presets = db.relationship("PublisherPreset", back_populates="publisher")

    def __init__(self, name, description, type, parameters):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type
        self.parameters = parameters

    @classmethod
    def get(cls, search) -> tuple[list["Publisher"], int]:
        query = cls.query

        if search is not None:
            query = query.filter(
                or_(
                    Publisher.name.ilike(f"%{search}%"),
                    Publisher.description.ilike(f"%{search}%"),
                )
            )

        return query.order_by(db.asc(Publisher.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        publishers, count = cls.get(search)
        items = [publisher.to_dict() for publisher in publishers]
        return {"total_count": count, "items": items}

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "parameters": [parameter.to_dict() for parameter in self.parameters],
        }

    @classmethod
    def load_multiple(cls, data: list[dict[str, Any]]) -> list["Publisher"]:
        return [cls.from_dict(publisher_data) for publisher_data in data]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Publisher":
        parameters = [Parameter.find_by_key(param_id) for param_id in data.pop("parameters", [])]
        return cls(parameters=parameters, **data)

    @classmethod
    def add(cls, data) -> tuple[str, int]:
        if cls.find_by_type(data["type"]):
            return "Publisher type already exists", 400

        publisher = cls.from_dict(data)

        db.session.add(publisher)
        db.session.commit()
        return f"Updated publisher {publisher.id}", 200

    @classmethod
    def get_first(cls):
        return cls.query.first()

    @classmethod
    def find_by_id(cls, id):
        return cls.query.filter_by(id=id).first()

    @classmethod
    def find_by_type(cls, type):
        return cls.query.filter_by(type=type).first()


class PublisherParameter(BaseModel):
    publisher_id = db.Column(db.String, db.ForeignKey("publisher.id"), primary_key=True)
    parameter_key = db.Column(db.String, db.ForeignKey("parameter.key"), primary_key=True)

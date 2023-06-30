import uuid
from sqlalchemy import or_
from typing import Any

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.parameter import Parameter


class Presenter(BaseModel):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    type = db.Column(db.String(), nullable=False)

    parameters = db.relationship("Parameter", secondary="presenter_parameter")

    node_id = db.Column(db.String, db.ForeignKey("presenters_node.id"))
    node = db.relationship("PresentersNode", back_populates="presenters")

    product_types = db.relationship("ProductType", back_populates="presenter")

    def __init__(self, name, description, type, parameters):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type
        self.parameters = parameters

    @classmethod
    def get_by_filter(cls, search):
        query = cls.query

        if search is not None:
            query = query.filter(
                or_(
                    Presenter.name.ilike(f"%{search}%"),
                    Presenter.description.ilike(f"%{search}%"),
                )
            )

        return query.order_by(db.asc(Presenter.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        presenters, count = cls.get_by_filter(search)
        items = [presenter.to_dict() for presenter in presenters]
        return {"total_count": count, "items": items}

    @classmethod
    def load_multiple(cls, data: list[dict[str, Any]]) -> list["Presenter"]:
        return [cls.from_dict(publisher_data) for publisher_data in data]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Presenter":
        parameters = [Parameter.find_by_key(param_id) for param_id in data.pop("parameters", [])]
        return cls(parameters=parameters, **data)

    @classmethod
    def add(cls, data) -> tuple[str, int]:
        if cls.find_by_type(data["type"]):
            return "Presenter type already exists", 400

        presenter = cls.from_dict(data)

        db.session.add(presenter)
        db.session.commit()
        return f"Updated presenter {presenter.id}", 200

    @classmethod
    def get_first(cls):
        return cls.query.first()

    @classmethod
    def find_by_id(cls, id):
        return cls.query.filter_by(id=id).first()

    @classmethod
    def find_by_type(cls, type):
        return cls.query.filter_by(type=type).first()

    def to_dict(self: "Presenter") -> dict[str, Any]:
        data = super().to_dict()
        data["parameters"] = [parameter.to_dict() for parameter in self.parameters]
        data["product_types"] = [product_type.id for product_type in self.product_types]
        return data


class PresenterParameter(BaseModel):
    presenter_id = db.Column(db.String, db.ForeignKey("presenter.id"), primary_key=True)
    parameter_key = db.Column(db.String, db.ForeignKey("parameter.key"), primary_key=True)

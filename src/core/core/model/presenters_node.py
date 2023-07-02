from typing import Any
from sqlalchemy import or_
import uuid

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.presenter import Presenter


class PresentersNode(BaseModel):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), unique=True, nullable=False)
    description = db.Column(db.String())

    api_url = db.Column(db.String(), nullable=False)
    api_key = db.Column(db.String(), nullable=False)

    presenters = db.relationship("Presenter", back_populates="node", cascade="all")

    def __init__(self, name, description, api_url, api_key, id=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.api_url = api_url
        self.api_key = api_key

    @classmethod
    def exists_by_api_key(cls, api_key):
        return db.session.query(db.exists().where(PresentersNode.api_key == api_key)).scalar()

    @classmethod
    def get_by_api_key(cls, api_key):
        return cls.query.filter_by(api_key=api_key).first()

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(PresentersNode.name)).all()

    @classmethod
    def get_by_filter(cls, search):
        query = cls.query

        if search is not None:
            query = query.filter(
                or_(
                    PresentersNode.name.ilike(f"%{search}%"),
                    PresentersNode.description.ilike(f"%{search}%"),
                )
            )

        return query.order_by(db.asc(PresentersNode.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        nodes, count = cls.get_by_filter(search)
        items = [node.to_dict() for node in nodes]
        return {"total_count": count, "items": items}

    @classmethod
    def update(cls, node_id, node_data, presenters):
        node = cls.query.get(node_id)
        updated_node = cls.from_dict(node_data)
        node.name = updated_node.name
        node.description = updated_node.description
        node.api_url = updated_node.api_url
        node.api_key = updated_node.api_key
        for presenter in presenters:
            found = any(presenter.type == existing_presenter.type for existing_presenter in node.presenters)
            if not found:
                node.presenters.append(presenter)

        db.session.commit()

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["presenters"] = [presenter.to_dict() for presenter in self.presenters]
        data["tag"] = "mdi-file-table-outline"
        data["type"] = "presenter"
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PresentersNode":
        presenter_data = data.pop("presenters", None)
        node = cls(**data)
        if presenter_data:
            node.presenters = [Presenter.from_dict(p) for p in presenter_data]
        return node

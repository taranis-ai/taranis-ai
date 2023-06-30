from typing import Any
from sqlalchemy import func, or_
import uuid

from core.managers.db_manager import db
from core.model.base_model import BaseModel


class BotsNode(BaseModel):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), unique=True, nullable=False)
    description = db.Column(db.String())
    api_url = db.Column(db.String(), nullable=False)
    api_key = db.Column(db.String(), nullable=False)

    def __init__(self, name, description, api_url, api_key, id=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.api_url = api_url
        self.api_key = api_key

    @classmethod
    def exists_by_api_key(cls, api_key):
        return db.session.query(db.exists().where(BotsNode.api_key == api_key)).scalar()

    @classmethod
    def get_by_api_key(cls, api_key):
        return cls.query.filter_by(api_key=api_key).first()

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(BotsNode.name)).all()

    @classmethod
    def get_by_filter(cls, search):
        query = cls.query

        if search is not None:
            query = query.filter(
                or_(
                    BotsNode.name.ilike(f"%{search}%"),
                    BotsNode.description.ilike(f"%{search}%"),
                )
            )

        return query.order_by(db.asc(BotsNode.name)).all(), query.count()

    @classmethod
    def get_json_by_id(cls, id):
        return cls.get(id).to_dict()

    @classmethod
    def get_all_json(cls, search):
        nodes, count = cls.get_by_filter(search)
        items = [node.to_dict() for node in nodes]
        return {"total_count": count, "items": items}

    @classmethod
    def update(cls, node_id, node_data):
        node = cls.query.get(node_id)
        updated_node = cls.from_dict(node_data)
        node.name = updated_node.name
        node.description = updated_node.description
        node.api_url = updated_node.api_url
        node.api_key = updated_node.api_key
        db.session.commit()

    @classmethod
    def get_first(cls):
        return cls.query.first()

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["tag"] = "mdi-robot"
        data["type"] = "bot"
        return data

from sqlalchemy import or_
import uuid

from core.managers.db_manager import db
from core.model.base_model import BaseModel


class PublishersNode(BaseModel):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), unique=True, nullable=False)
    description = db.Column(db.String())

    api_url = db.Column(db.String(), nullable=False)
    api_key = db.Column(db.String(), nullable=False)

    publishers = db.relationship("Publisher", back_populates="node", cascade="all")

    def __init__(self, name, description, api_url, api_key, id=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.api_url = api_url
        self.api_key = api_key

    @classmethod
    def exists_by_api_key(cls, api_key):
        return db.session.query(db.exists().where(PublishersNode.api_key == api_key)).scalar()

    @classmethod
    def get_by_api_key(cls, api_key):
        return cls.query.filter_by(api_key=api_key).first()

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(PublishersNode.name)).all()

    @classmethod
    def get_by_filter(cls, search):
        query = cls.query

        if search:
            query = query.filter(
                or_(
                    PublishersNode.name.ilike(f"%{search}%"),
                    PublishersNode.description.ilike(f"%{search}%"),
                )
            )

        return query.order_by(db.asc(PublishersNode.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        nodes, count = cls.get_by_filter(search)
        items = [node.to_dict() for node in nodes]
        return {"total_count": count, "items": items}

    @classmethod
    def add(cls, node_data, publishers) -> "PublishersNode":
        node = cls.from_dict(node_data)
        node.publishers = publishers
        db.session.add(node)
        db.session.commit()
        return node

    @classmethod
    def update(cls, node_id, node_data, publishers):
        node = cls.get(node_id)
        updated_node = cls.from_dict(node_data)
        node.name = updated_node.name
        node.description = updated_node.description
        node.api_url = updated_node.api_url
        node.api_key = updated_node.api_key
        for publisher in publishers:
            found = any(publisher.type == existing_publisher.type for existing_publisher in node.publishers)
            if not found:
                node.publishers.append(publisher)

        db.session.commit()

    def to_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["publishers"] = [publisher.id for publisher in self.publishers]
        data["tag"] = "mdi-file-star-outline"
        return data

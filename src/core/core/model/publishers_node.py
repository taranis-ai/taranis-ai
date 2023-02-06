from marshmallow import post_load
from sqlalchemy import func, or_, orm
import uuid

from core.managers.db_manager import db
from shared.schema.publishers_node import (
    PublishersNodeSchema,
    PublishersNodePresentationSchema,
)


class NewPublishersNodeSchema(PublishersNodeSchema):
    @post_load
    def make(self, data, **kwargs):
        return PublishersNode(**data)


class PublishersNode(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), unique=True, nullable=False)
    description = db.Column(db.String())

    api_url = db.Column(db.String(), nullable=False)
    api_key = db.Column(db.String(), nullable=False)

    publishers = db.relationship("Publisher", back_populates="node", cascade="all")

    def __init__(self, id, name, description, api_url, api_key):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.api_url = api_url
        self.api_key = api_key
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-file-star-outline"

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
    def get(cls, search):
        query = cls.query

        if search is not None:
            search_string = "%" + search.lower() + "%"
            query = query.filter(
                or_(
                    func.lower(PublishersNode.name).like(search_string),
                    func.lower(PublishersNode.description).like(search_string),
                )
            )

        return query.order_by(db.asc(PublishersNode.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        nodes, count = cls.get(search)
        node_schema = PublishersNodePresentationSchema(many=True)
        return {"total_count": count, "items": node_schema.dump(nodes)}

    @classmethod
    def add_new(cls, node_data, publishers):
        new_node_schema = NewPublishersNodeSchema()
        node = new_node_schema.load(node_data)
        node.publishers = publishers
        db.session.add(node)
        db.session.commit()

    @classmethod
    def update(cls, node_id, node_data, publishers):
        new_node_schema = NewPublishersNodeSchema()
        updated_node = new_node_schema.load(node_data)
        node = cls.query.get(node_id)
        node.name = updated_node.name
        node.description = updated_node.description
        node.api_url = updated_node.api_url
        node.api_key = updated_node.api_key
        for publisher in publishers:
            found = False
            for existing_publisher in node.publishers:
                if publisher.type == existing_publisher.type:
                    found = True
                    break

            if found is False:
                node.publishers.append(publisher)

        db.session.commit()

    @classmethod
    def delete(cls, node_id):
        node = cls.query.get(node_id)
        for publisher in node.publishers:
            if len(publisher.presets) > 0:
                raise Exception("Presenters has mapped presets")

        db.session.delete(node)
        db.session.commit()

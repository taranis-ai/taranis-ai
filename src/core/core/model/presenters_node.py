from marshmallow import post_load
from sqlalchemy import func, or_, orm
import uuid

from core.managers.db_manager import db
from shared.schema.presenters_node import (
    PresentersNodeSchema,
    PresentersNodePresentationSchema,
)


class NewPresentersNodeSchema(PresentersNodeSchema):
    @post_load
    def make(self, data, **kwargs):
        return PresentersNode(**data)


class PresentersNode(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), unique=True, nullable=False)
    description = db.Column(db.String())

    api_url = db.Column(db.String(), nullable=False)
    api_key = db.Column(db.String(), nullable=False)

    presenters = db.relationship("Presenter", back_populates="node", cascade="all")

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
        self.tag = "mdi-file-table-outline"

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
    def get(cls, search):
        query = cls.query

        if search is not None:
            search_string = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(PresentersNode.name).like(search_string),
                    func.lower(PresentersNode.description).like(search_string),
                )
            )

        return query.order_by(db.asc(PresentersNode.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        nodes, count = cls.get(search)
        node_schema = PresentersNodePresentationSchema(many=True)
        return {"total_count": count, "items": node_schema.dump(nodes)}

    @classmethod
    def add_new(cls, node_data, presenters):
        new_node_schema = NewPresentersNodeSchema()
        node = new_node_schema.load(node_data)
        node.presenters = presenters
        db.session.add(node)
        db.session.commit()

    @classmethod
    def update(cls, node_id, node_data, presenters):
        new_node_schema = NewPresentersNodeSchema()
        updated_node = new_node_schema.load(node_data)
        node = cls.query.get(node_id)
        node.name = updated_node.name
        node.description = updated_node.description
        node.api_url = updated_node.api_url
        node.api_key = updated_node.api_key
        for presenter in presenters:
            found = False
            for existing_presenter in node.presenters:
                if presenter.type == existing_presenter.type:
                    found = True
                    break

            if found is False:
                node.presenters.append(presenter)

        db.session.commit()

    @classmethod
    def delete(cls, node_id):
        node = cls.query.get(node_id)
        for presenter in node.presenters:
            if len(presenter.product_types) > 0:
                raise Exception("Presenters has mapped product types")

        db.session.delete(node)
        db.session.commit()

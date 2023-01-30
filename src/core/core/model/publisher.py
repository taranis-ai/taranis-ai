from marshmallow import post_load
import uuid
from sqlalchemy import or_, func

from core.managers.db_manager import db
from core.model.parameter import Parameter
from shared.schema.publisher import PublisherSchema


class NewPublisherSchema(PublisherSchema):
    @post_load
    def make(self, data, **kwargs):
        return Publisher(**data)


class Publisher(db.Model):
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
    def get(cls, search):
        query = cls.query

        if search is not None:
            search_string = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Publisher.name).like(search_string),
                    func.lower(Publisher.description).like(search_string),
                )
            )

        return query.order_by(db.asc(Publisher.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        publisher, count = cls.get(search)
        node_schema = PublisherSchema(many=True)
        items = node_schema.dump(publisher)

        return {"total_count": count, "items": items}

    @classmethod
    def create_all(cls, publishers_data):
        new_publisher_schema = NewPublisherSchema(many=True)
        return new_publisher_schema.load(publishers_data)

    @classmethod
    def add(cls, data):
        if cls.find_by_type(data["type"]):
            return None
        schema = NewPublisherSchema()

        parameters = [Parameter.find_by_key(p) for p in data["parameters"] if p is not None]
        data["parameters"] = []
        publisher = schema.load(data)
        publisher.parameters = parameters

        db.session.add(publisher)
        db.session.commit()

    @classmethod
    def get_first(cls):
        return cls.query.first()

    @classmethod
    def find_by_id(cls, id):
        return cls.query.filter_by(id=id).first()

    @classmethod
    def find_by_type(cls, type):
        return cls.query.filter_by(type=type).first()


class PublisherParameter(db.Model):
    publisher_id = db.Column(db.String, db.ForeignKey("publisher.id"), primary_key=True)
    parameter_key = db.Column(db.String, db.ForeignKey("parameter.key"), primary_key=True)

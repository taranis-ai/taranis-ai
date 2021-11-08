from marshmallow import fields, post_load
import uuid

from managers.db_manager import db
from model.parameter import NewParameterSchema
from schema.publisher import PublisherSchema


class NewPublisherSchema(PublisherSchema):
    parameters = fields.List(fields.Nested(NewParameterSchema))

    @post_load
    def make(self, data, **kwargs):
        return Publisher(**data)


class Publisher(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    type = db.Column(db.String(), nullable=False)

    parameters = db.relationship('Parameter', secondary='publisher_parameter')

    node_id = db.Column(db.String, db.ForeignKey('publishers_node.id'))
    node = db.relationship("PublishersNode", back_populates="publishers")

    presets = db.relationship('PublisherPreset', back_populates="publisher")

    def __init__(self, name, description, type, parameters):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type
        self.parameters = parameters

    @classmethod
    def create_all(cls, publishers_data):
        new_publisher_schema = NewPublisherSchema(many=True)
        return new_publisher_schema.load(publishers_data)


class PublisherParameter(db.Model):
    publisher_id = db.Column(db.String, db.ForeignKey('publisher.id'), primary_key=True)
    parameter_id = db.Column(db.Integer, db.ForeignKey('parameter.id'), primary_key=True)

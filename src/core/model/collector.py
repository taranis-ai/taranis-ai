from marshmallow import fields, post_load
import uuid

from managers.db_manager import db
from model.parameter import NewParameterSchema
from schema.collector import CollectorSchema


class NewCollectorSchema(CollectorSchema):
    parameters = fields.List(fields.Nested(NewParameterSchema))

    @post_load
    def make_collector(self, data, **kwargs):
        return Collector(**data)


class Collector(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    type = db.Column(db.String(), nullable=False)

    parameters = db.relationship('Parameter', secondary='collector_parameter')

    node_id = db.Column(db.String, db.ForeignKey('collectors_node.id'))
    node = db.relationship("CollectorsNode", back_populates="collectors")

    sources = db.relationship('OSINTSource', back_populates="collector")

    def __init__(self, name, description, type, parameters):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type
        self.parameters = parameters

    @classmethod
    def create_all(cls, collectors_data):
        new_collector_schema = NewCollectorSchema(many=True)
        return new_collector_schema.load(collectors_data)


class CollectorParameter(db.Model):
    collector_id = db.Column(db.String, db.ForeignKey('collector.id'), primary_key=True)
    parameter_id = db.Column(db.Integer, db.ForeignKey('parameter.id'), primary_key=True)

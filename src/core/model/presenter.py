from marshmallow import fields, post_load
import uuid

from managers.db_manager import db
from model.parameter import NewParameterSchema
from schema.presenter import PresenterSchema


class NewPresenterSchema(PresenterSchema):
    parameters = fields.List(fields.Nested(NewParameterSchema))

    @post_load
    def make(self, data, **kwargs):
        return Presenter(**data)


class Presenter(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    type = db.Column(db.String(), nullable=False)

    parameters = db.relationship('Parameter', secondary='presenter_parameter')

    node_id = db.Column(db.String, db.ForeignKey('presenters_node.id'))
    node = db.relationship("PresentersNode", back_populates="presenters")

    product_types = db.relationship('ProductType', back_populates="presenter")

    def __init__(self, name, description, type, parameters):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type
        self.parameters = parameters

    @classmethod
    def create_all(cls, presenters_data):
        new_presenter_schema = NewPresenterSchema(many=True)
        return new_presenter_schema.load(presenters_data)


class PresenterParameter(db.Model):
    presenter_id = db.Column(db.String, db.ForeignKey('presenter.id'), primary_key=True)
    parameter_id = db.Column(db.Integer, db.ForeignKey('parameter.id'), primary_key=True)

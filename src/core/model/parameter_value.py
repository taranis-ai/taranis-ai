from marshmallow import post_load, fields

from managers.db_manager import db
from schema.parameter_value import ParameterValueSchema


class NewParameterValueSchema(ParameterValueSchema):

    @post_load
    def make_parameter_value(self, data, **kwargs):
        return ParameterValue(**data)


class ParameterValue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(), nullable=False)

    parameter_id = db.Column(db.Integer, db.ForeignKey('parameter.id'))
    parameter = db.relationship("Parameter")

    def __init__(self, value, parameter):
        self.id = None
        self.value = value
        self.parameter_id = parameter.id

from marshmallow import post_load

from core.managers.db_manager import db
from marshmallow import fields
from shared.schema.parameter_value import ParameterValueSchema
from shared.schema.parameter import ParameterSchema


class NewParameterValueSchema(ParameterValueSchema):
    parameter = fields.Nested(ParameterSchema)

    @post_load
    def make_parameter_value(self, data, **kwargs):
        return ParameterValue(**data)


class ParameterValueImportSchema(ParameterValueSchema):
    @post_load
    def make_parameter_value(self, data, **kwargs):
        return ParameterValue(**data)


class ParameterValue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(), nullable=False, default="")

    parameter_key = db.Column(db.String(), db.ForeignKey("parameter.key"))
    parameter = db.relationship("Parameter")

    def __init__(self, value, parameter):
        self.id = None
        self.value = value
        self.parameter_key = parameter

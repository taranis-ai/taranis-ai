from marshmallow import Schema, fields, post_load

from schema.parameter import ParameterSchema


class ParameterValueSchema(Schema):
    value = fields.Str(missing='')
    parameter = fields.Nested(ParameterSchema)

    @post_load
    def make_parameter_value(self, data, **kwargs):
        return ParameterValue(**data)


class ParameterValue:

    def __init__(self, value, parameter):
        self.value = value
        self.parameter = parameter

from marshmallow import Schema, fields, post_load

from schema.parameter import ParameterSchema, ParameterExportSchema


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


class ParameterValueExportSchema(Schema):
    value = fields.Str(missing='')
    parameter = fields.Nested(ParameterExportSchema)

    @post_load
    def make(self, data, **kwargs):
        return ParameterValueExport(**data)


class ParameterValueExport:

    def __init__(self, value, parameter):
        self.value = value
        self.parameter = parameter

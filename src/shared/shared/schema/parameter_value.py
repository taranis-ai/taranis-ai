from marshmallow import Schema, fields, post_load

from shared.schema.parameter import ParameterExportSchema


class ParameterValueImportSchema(Schema):
    value = fields.Str(load_default="")
    parameter = fields.Nested(ParameterExportSchema)


class ParameterValueSchema(Schema):
    value = fields.Str(load_default="")
    parameter = fields.Str()


class ParameterValueExportSchema(Schema):
    value = fields.Str(load_default="")
    parameter = fields.Nested(ParameterExportSchema)

    @post_load
    def make(self, data, **kwargs):
        return ParameterValueExport(**data)


class ParameterValueExport:
    def __init__(self, value, parameter):
        self.value = value
        self.parameter = parameter

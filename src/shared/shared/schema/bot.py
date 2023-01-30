from marshmallow import Schema, fields

from shared.schema.parameter_value import ParameterValueExportSchema, ParameterValueImportSchema


class BotSchema(Schema):
    id = fields.Str()
    type = fields.Str()
    name = fields.Str()
    description = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueExportSchema))


class BotImportSchema(Schema):
    id = fields.Str()
    type = fields.Str()
    name = fields.Str()
    description = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueImportSchema))

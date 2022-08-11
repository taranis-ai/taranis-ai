from marshmallow import Schema, fields

from shared.schema.parameter import ParameterSchema


class BotSchema(Schema):
    id = fields.Str()
    type = fields.Str()
    name = fields.Str()
    description = fields.Str()
    parameters = fields.List(fields.Nested(ParameterSchema))

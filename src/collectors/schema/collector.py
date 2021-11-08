from marshmallow import Schema, fields

from schema import parameter


class CollectorSchema(Schema):
    id = fields.Str()
    type = fields.Str()
    name = fields.Str()
    description = fields.Str()
    parameters = fields.List(fields.Nested(parameter.ParameterSchema))

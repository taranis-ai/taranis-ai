from marshmallow import Schema, fields, post_load

from schema.parameter import ParameterSchema


class CollectorSchema(Schema):
    id = fields.Str()
    type = fields.Str()
    name = fields.Str()
    description = fields.Str()
    parameters = fields.List(fields.Nested(ParameterSchema))


class CollectorExportSchema(Schema):
    type = fields.Str()

    @post_load
    def make(self, data, **kwargs):
        return CollectorExport(**data)


class CollectorExport:

    def __init__(self, type):
        self.type = type

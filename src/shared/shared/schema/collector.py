from marshmallow import Schema, fields, post_load

from shared.schema.parameter import ParameterSchema
from enum import Enum, auto


class CollectorType(Enum):
    EMAIL_COLLECTOR = auto()
    WEB_COLLECTOR = auto()
    ATOM_COLLECTOR = auto()
    TWITTER_COLLECTOR = auto()
    RSS_COLLECTOR = auto()
    MANUAL_COLLECTOR = auto()
    SLACK_COLLECTOR = auto()


class CollectorSchema(Schema):
    id = fields.Str()
    type = fields.Str()
    name = fields.Str()
    description = fields.Str()
    parameters = fields.List(fields.Nested(ParameterSchema))


class CollectorSchemaWithOutParameters(Schema):
    id = fields.Str()
    type = fields.Str()
    name = fields.Str()
    description = fields.Str()


class CollectorExportSchema(Schema):
    type = fields.Str()

    @post_load
    def make(self, data, **kwargs):
        return CollectorExport(**data)


class CollectorExport:
    def __init__(self, type):
        self.type = type

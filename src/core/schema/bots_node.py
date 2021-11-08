from marshmallow import Schema, fields, post_load, EXCLUDE

from schema.presentation import PresentationSchema
from schema.bot import BotSchema


class BotsNodeSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    api_url = fields.Str()
    api_key = fields.Str()
    bots = fields.List(fields.Nested(BotSchema))

    @post_load
    def make(self, data, **kwargs):
        return BotsNode(**data)


class BotsNodePresentationSchema(BotsNodeSchema, PresentationSchema):
    pass


class BotsNode:

    def __init__(self, id, name, description, api_url, api_key):
        self.id = id
        self.name = name
        self.description = description
        self.api_url = api_url
        self.api_key = api_key

    @classmethod
    def create(cls, data):
        node_schema = BotsNodeSchema()
        return node_schema.load(data)

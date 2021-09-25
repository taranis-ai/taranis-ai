from marshmallow import Schema, fields, post_load
from taranisng.schema.collector import CollectorSchema
from taranisng.schema.presentation import PresentationSchema


class CollectorsNodeSchema(Schema):
    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    api_url = fields.Str()
    api_key = fields.Str()
    collectors = fields.List(fields.Nested(CollectorSchema))

    @post_load
    def make_collectors_node(self, data, **kwargs):
        return CollectorsNode(**data)


class CollectorsNodePresentationSchema(CollectorsNodeSchema, PresentationSchema):
    pass


class CollectorsNode:

    def __init__(self, id, name, description, api_url, api_key, collectors):
        self.id = id
        self.name = name
        self.description = description
        self.api_url = api_url
        self.api_key = api_key
        self.collectors = collectors

    @classmethod
    def create(cls, data):
        node_schema = CollectorsNodeSchema()
        return node_schema.load(data)

from marshmallow import Schema, fields, post_load, EXCLUDE

from shared.schema.publisher import PublisherSchema
from shared.schema.presentation import PresentationSchema


class PublishersNodeSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    api_url = fields.Str()
    api_key = fields.Str()
    publishers = fields.List(fields.Nested(PublisherSchema))

    @post_load
    def make(self, data, **kwargs):
        return PublishersNode(**data)


class PublishersNodePresentationSchema(PublishersNodeSchema, PresentationSchema):
    pass


class PublishersNode:
    def __init__(self, id, name, description, api_url, api_key):
        self.id = id
        self.name = name
        self.description = description
        self.api_url = api_url
        self.api_key = api_key

    @classmethod
    def create(cls, data):
        node_schema = PublishersNodeSchema()
        return node_schema.load(data)

from marshmallow import Schema, fields, post_load, EXCLUDE

from shared.schema.presenter import PresenterSchema
from shared.schema.presentation import PresentationSchema


class PresentersNodeSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    api_url = fields.Str()
    api_key = fields.Str()
    presenters = fields.List(fields.Nested(PresenterSchema))

    @post_load
    def make(self, data, **kwargs):
        return PresentersNode(**data)


class PresentersNodePresentationSchema(PresentersNodeSchema, PresentationSchema):
    pass


class PresentersNode:
    def __init__(self, id, name, description, api_url, api_key):
        self.id = id
        self.name = name
        self.description = description
        self.api_url = api_url
        self.api_key = api_key

    @classmethod
    def create(cls, data):
        node_schema = PresentersNodeSchema()
        return node_schema.load(data)

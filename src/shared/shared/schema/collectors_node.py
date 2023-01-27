from marshmallow import Schema, fields, post_load


class CollectorsNodeSchema(Schema):
    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    api_url = fields.Str()
    api_key = fields.Str()

    @post_load
    def make_collectors_node(self, data, **kwargs):
        return CollectorsNode(**data)


class CollectorsNodePresentationSchema(CollectorsNodeSchema):
    type = fields.Str()
    tag = fields.Str()


class CollectorsNode:
    def __init__(self, id, name, description, api_url, api_key):
        self.id = id
        self.name = name
        self.description = description
        self.api_url = api_url
        self.api_key = api_key

    @classmethod
    def create(cls, data):
        node_schema = CollectorsNodeSchema()
        return node_schema.load(data)

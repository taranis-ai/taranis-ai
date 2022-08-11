from marshmallow import Schema, fields, post_load, EXCLUDE

from shared.schema.address import AddressSchema
from shared.schema.presentation import PresentationSchema


class OrganizationSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    description = fields.Str()
    address = fields.Nested(AddressSchema)


class OrganizationPresentationSchema(OrganizationSchema, PresentationSchema):
    pass


class OrganizationIdSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()

    @post_load
    def make(self, data, **kwargs):
        return OrganizationId(**data)


class OrganizationId:
    def __init__(self, id):
        self.id = id

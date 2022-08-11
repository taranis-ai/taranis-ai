from marshmallow import Schema, fields, EXCLUDE

from core.schema.presentation import PresentationSchema
from core.schema.report_item import ReportItemPresentationSchema
from core.schema.acl_entry import ACLEntryStatusSchema


class ProductSchemaBase(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    product_type_id = fields.Int()


class ProductSchema(ProductSchemaBase):
    report_items = fields.Nested(ReportItemPresentationSchema, many=True)


class ProductPresentationSchema(ProductSchema, ACLEntryStatusSchema, PresentationSchema):
    pass

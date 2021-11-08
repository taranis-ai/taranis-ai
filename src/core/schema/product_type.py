from marshmallow import Schema, fields, EXCLUDE

from schema.parameter_value import ParameterValueSchema
from schema.presentation import PresentationSchema


class ProductTypeSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    presenter_id = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))


class ProductTypePresentationSchema(ProductTypeSchema, PresentationSchema):
    pass

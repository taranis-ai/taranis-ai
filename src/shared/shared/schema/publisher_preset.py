from marshmallow import Schema, fields, EXCLUDE

from shared.schema.parameter_value import ParameterValueExportSchema
from shared.schema.presentation import PresentationSchema


class PublisherPresetSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    use_for_notifications = fields.Bool()
    publisher_id = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueExportSchema))


class PublisherPresetPresentationSchema(PublisherPresetSchema, PresentationSchema):
    pass

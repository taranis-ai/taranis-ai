from marshmallow import Schema, fields, post_load, EXCLUDE

from schema.parameter_value import ParameterValueSchema
from schema.presentation import PresentationSchema


class PublisherPresetSchemaBase(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str()
    name = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))

    @post_load
    def make(self, data, **kwargs):
        return PublisherPreset(**data)


class PublisherPresetSchema(PublisherPresetSchemaBase):
    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    use_for_notifications = fields.Bool()
    publisher_id = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))


class PublisherPresetPresentationSchema(PublisherPresetSchema, PresentationSchema):
    pass


class PublisherPreset:

    def __init__(self, id, name, parameter_values):
        self.id = id
        self.name = name

        self.parameter_values = dict()
        for parameter_value in parameter_values:
            self.parameter_values.update({parameter_value.parameter.key: parameter_value.value})

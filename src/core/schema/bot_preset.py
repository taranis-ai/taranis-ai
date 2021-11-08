from marshmallow import Schema, fields, post_load, EXCLUDE

from schema.parameter_value import ParameterValueSchema
from schema.presentation import PresentationSchema


class BotPresetSchemaBase(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str()
    name = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))

    @post_load
    def make(self, data, **kwargs):
        return BotPreset(**data)


class BotPresetSchema(BotPresetSchemaBase):
    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    bot_id = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))


class BotPresetPresentationSchema(BotPresetSchema, PresentationSchema):
    pass


class BotPreset:

    def __init__(self, id, name, parameter_values):
        self.id = id
        self.name = name

        self.parameter_values = dict()
        for parameter_value in parameter_values:
            self.parameter_values.update({parameter_value.parameter.key: parameter_value.value})

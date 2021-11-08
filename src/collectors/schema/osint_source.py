from marshmallow import Schema, fields, post_load, EXCLUDE

from schema.parameter_value import ParameterValueSchema
from schema.word_list import WordListSchema
from schema.presentation import PresentationSchema
from schema.collector import CollectorSchema


class OSINTSourceSchemaBase(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str()
    name = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))
    word_lists = fields.List(fields.Nested(WordListSchema))

    @post_load
    def make_osint_source(self, data, **kwargs):
        return OSINTSource(**data)

class OSINTSourceUpdateStatusSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    last_collected = fields.DateTime('%d.%m.%Y - %H:%M:%s')
    last_attempted = fields.DateTime('%d.%m.%Y - %H:%M:%s')
    last_error_message = fields.Str()
    last_data = fields.Raw()

class OSINTSourceSchema(OSINTSourceSchemaBase):
    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    collector_id = fields.Str()


class OSINTSourcePresentationSchema(OSINTSourceSchema, PresentationSchema):
    collector = fields.Nested(CollectorSchema)


class OSINTSourceIdSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str()

    @post_load
    def make(self, data, **kwargs):
        return OSINTSourceId(**data)


class OSINTSourceId:

    def __init__(self, id):
        self.id = id


class OSINTSource:

    def __init__(self, id, name, parameter_values, word_lists):
        self.id = id
        self.name = name

        self.parameter_values = dict()
        for parameter_value in parameter_values:
            self.parameter_values.update({parameter_value.parameter.key: parameter_value.value})

        self.word_lists = word_lists

class OSINTSourceGroupSchema(Schema):
    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    osint_sources = fields.List(fields.Nested(OSINTSourceSchema))


class OSINTSourceGroupPresentationSchema(OSINTSourceGroupSchema, PresentationSchema):
    pass

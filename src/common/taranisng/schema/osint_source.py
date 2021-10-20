from marshmallow import Schema, fields, post_load, EXCLUDE
from taranisng.schema.parameter_value import ParameterValueSchema
from taranisng.schema.word_list import WordListSchema
from taranisng.schema.presentation import PresentationSchema
from taranisng.schema.collector import CollectorSchema


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

from marshmallow import Schema, fields, post_load, EXCLUDE

from shared.schema.collector import CollectorSchema, CollectorExportSchema
from shared.schema.parameter_value import ParameterValueSchema, ParameterValueExportSchema, ParameterValueImportSchema
from shared.schema.presentation import PresentationSchema
from shared.schema.word_list import WordListSchema


class OSINTSourceGroupSchemaBase(Schema):
    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    default = fields.Bool()


class OSINTSourceGroupIdSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str()

    @post_load
    def make(self, data, **kwargs):
        return OSINTSourceGroupId(**data)


class OSINTSourceGroupId:
    def __init__(self, id):
        self.id = id


class OSINTSourceSchemaBase(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str()
    name = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueExportSchema))
    word_lists = fields.List(fields.Nested(WordListSchema))

    @post_load
    def make_osint_source(self, data, **kwargs):
        return OSINTSource(**data)


class OSINTSourceUpdateStatusSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    last_collected = fields.DateTime("%d.%m.%Y - %H:%M:%s")
    last_attempted = fields.DateTime("%d.%m.%Y - %H:%M:%s")
    last_error_message = fields.Str()
    last_data = fields.Raw()


class OSINTSourceSchema(OSINTSourceSchemaBase):
    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    collector_id = fields.Str()


class OSINTSourceCollectorSchema(Schema):
    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    collector_type = fields.Str()


class OSINTSourcePresentationSchema(OSINTSourceSchema, PresentationSchema):
    collector = fields.Nested(CollectorSchema)
    osint_source_groups = fields.Nested(OSINTSourceSchemaBase, many=True, allow_none=True)


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


class OSINTSourceGroupSchema(OSINTSourceGroupSchemaBase):
    osint_sources = fields.List(fields.Nested(OSINTSourceSchema))


class OSINTSourceGroupPresentationSchema(OSINTSourceGroupSchema, PresentationSchema):
    pass


class OSINTSourceExportSchema(Schema):
    name = fields.Str()
    description = fields.Str()
    collector = fields.Nested(CollectorExportSchema)
    parameter_values = fields.List(fields.Nested(ParameterValueImportSchema))

    @post_load
    def make(self, data, **kwargs):
        return OSINTSourceExport(**data)


class OSINTSourceExport:
    def __init__(self, name, description, collector, parameter_values):
        self.name = name
        self.description = description
        self.collector = collector
        self.parameter_values = parameter_values



class OSINTSourceExportRootSchema(Schema):
    version = fields.Int()
    data = fields.Nested(OSINTSourceExportSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        return OSINTSourceExportRoot(**data)


class OSINTSourceExportRoot:
    def __init__(self, version, data):
        self.version = version
        self.data = data

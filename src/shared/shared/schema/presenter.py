from marshmallow import Schema, fields, post_load

from shared.schema.parameter import ParameterSchema
from shared.schema.parameter_value import ParameterValueSchema
from shared.schema.report_item import ReportItemSchema
from shared.schema.report_item_type import ReportItemTypeSchema


class PresenterSchema(Schema):
    id = fields.Str()
    type = fields.Str()
    name = fields.Str()
    description = fields.Str()
    parameters = fields.List(fields.Nested(ParameterSchema))


class PresenterInputSchema(Schema):
    type = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))
    reports = fields.List(fields.Nested(ReportItemSchema))
    report_type = fields.Nested(ReportItemTypeSchema)

    @post_load
    def make(self, data, **kwargs):
        return PresenterInput(**data)


class PresenterInput:
    def __init__(self, type, parameter_values, reports, report_type):
        self.type = type
        self.parameter_values = parameter_values
        self.reports = reports
        self.report_type = report_type

        self.parameter_values_map = dict()
        for parameter_value in parameter_values:
            self.parameter_values_map.update({parameter_value.parameter.key: parameter_value.value})


class PresenterOutputSchema(Schema):
    mime_type = fields.Str()
    data = fields.Str()

    @post_load
    def make(self, data, **kwargs):
        return PresenterOutput(**data)


class PresenterOutput:
    def __init__(self, mime_type, data):
        self.mime_type = mime_type
        self.data = data

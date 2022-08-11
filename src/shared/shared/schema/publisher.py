from marshmallow import Schema, fields, post_load

from shared.schema.parameter import ParameterSchema
from shared.schema.parameter_value import ParameterValueSchema


class PublisherSchema(Schema):
    id = fields.Str()
    type = fields.Str()
    name = fields.Str()
    description = fields.Str()
    parameters = fields.List(fields.Nested(ParameterSchema))


class PublisherInputSchema(Schema):
    type = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))
    mime_type = fields.Str(allow_none=True)
    data = fields.Str(allow_none=True)
    message_title = fields.Str(allow_none=True)
    message_body = fields.Str(allow_none=True)
    recipients = fields.List(fields.String, allow_none=True)

    @post_load
    def make(self, data, **kwargs):
        return PublisherInput(**data)


class PublisherInput:
    def __init__(
        self,
        type,
        parameter_values,
        mime_type,
        data,
        message_title,
        message_body,
        recipients,
    ):
        self.type = type
        self.parameter_values = parameter_values
        self.mime_type = mime_type
        self.data = data
        self.message_title = message_title
        self.message_body = message_body
        self.recipients = recipients

        self.parameter_values_map = dict()
        for parameter_value in parameter_values:
            self.parameter_values_map.update({parameter_value.parameter.key: parameter_value.value})

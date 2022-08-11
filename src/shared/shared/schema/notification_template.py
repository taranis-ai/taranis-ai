from marshmallow import Schema, fields, EXCLUDE, post_load

from shared.schema.presentation import PresentationSchema


class EmailRecipientSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()
    email = fields.Str()
    name = fields.Str()


class NotificationTemplateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    description = fields.Str()
    message_title = fields.Str()
    message_body = fields.Str()


class NotificationTemplatePresentationSchema(NotificationTemplateSchema, PresentationSchema):
    recipients = fields.Nested(EmailRecipientSchema, many=True)


class NotificationTemplateIdSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()

    @post_load
    def make(self, data, **kwargs):
        return NotificationTemplateId(**data)


class NotificationTemplateId:
    def __init__(self, id):
        self.id = id

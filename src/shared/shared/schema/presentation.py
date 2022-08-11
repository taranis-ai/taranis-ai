from marshmallow import Schema, fields


class PresentationSchema(Schema):
    title = fields.Str()
    subtitle = fields.Str()
    tag = fields.Str()

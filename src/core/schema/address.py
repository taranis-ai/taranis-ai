from marshmallow import Schema, fields


class AddressSchema(Schema):
    street = fields.Str()
    city = fields.Str()
    zip = fields.Str()
    country = fields.Str()

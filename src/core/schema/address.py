from marshmallow import Schema, fields, EXCLUDE


class AddressSchema(Schema):
    street = fields.Str()
    city = fields.Str()
    zip = fields.Str()
    country = fields.Str()

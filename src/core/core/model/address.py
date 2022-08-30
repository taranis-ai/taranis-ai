from marshmallow import post_load

from core.managers.db_manager import db
from shared.schema.address import AddressSchema


class NewAddressSchema(AddressSchema):
    @post_load
    def make(self, data, **kwargs):
        return Address(**data)


class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    street = db.Column(db.String())
    city = db.Column(db.String())
    zip = db.Column(db.String())
    country = db.Column(db.String())

    def __init__(self, street, city, zip, country):
        self.id = None
        self.street = street
        self.city = city
        self.zip = zip
        self.country = country

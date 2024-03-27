from core.managers.db_manager import db
from core.model.base_model import BaseModel


class Address(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    street = db.Column(db.String())
    city = db.Column(db.String())
    zip = db.Column(db.String())
    country = db.Column(db.String())

    def __init__(self, street=None, city=None, zip=None, country=None, id=None):
        self.id = id
        self.street = street
        self.city = city
        self.zip = zip
        self.country = country

    def update_from_address(self, new_address: "Address") -> tuple[dict, int]:
        return self.update(new_address.to_dict())

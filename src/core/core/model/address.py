from sqlalchemy.orm import Mapped

from core.managers.db_manager import db
from core.model.base_model import BaseModel


class Address(BaseModel):
    __tablename__ = "address"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    street: Mapped[str] = db.Column(db.String())
    city: Mapped[str] = db.Column(db.String())
    zip: Mapped[str] = db.Column(db.String())
    country: Mapped[str] = db.Column(db.String())

    def __init__(self, street=None, city=None, zip=None, country=None, id=None):
        if id:
            self.id = id
        if street:
            self.street = street
        if city:
            self.city = city
        if zip:
            self.zip = zip
        if country:
            self.country = country

    def update_from_address(self, new_address: "Address") -> tuple[dict, int]:
        return self.update(new_address.to_dict())

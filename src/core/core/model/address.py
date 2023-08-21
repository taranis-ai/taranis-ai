from typing import Any

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.managers.log_manager import logger


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

    def update(self, new_item: dict[str, Any]) -> tuple[str, int]:
        for key, value in new_item.items():
            if hasattr(self, key) and key != "id":
                setattr(self, key, value)

        db.session.commit()
        return f"Successfully updated {self.id}", 200

    def update_from_address(self, new_address: "Address") -> tuple[str, int]:
        return self.update(new_address.to_dict())

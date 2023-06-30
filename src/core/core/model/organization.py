from sqlalchemy import or_
from typing import Any

from core.managers.db_manager import db
from core.model.address import Address
from core.model.base_model import BaseModel
from core.managers.log_manager import logger


class Organization(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    address_id = db.Column(db.Integer, db.ForeignKey("address.id"))
    address = db.relationship("Address", cascade="all")

    def __init__(self, name, description, address, id=None):
        self.id = id
        self.name = name
        self.description = description
        self.address = address

    def to_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["address"] = self.address.to_dict() if self.address else None
        data.pop("address_id")
        data["tag"] = "mdi-office-building"
        return data

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(Organization.name)).all()

    @classmethod
    def get_by_filter(cls, search):
        query = cls.query

        if search:
            query = query.filter(
                or_(
                    Organization.name.ilike(f"%{search}%"),
                    Organization.description.ilike(f"%{search}%"),
                )
            )

        return query.order_by(db.asc(Organization.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        organizations, count = cls.get_by_filter(search)
        items = [organization.to_dict() for organization in organizations]
        return {"total_count": count, "items": items}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Organization":
        address_data = data.pop("address", None)
        address = Address.from_dict(address_data) if address_data else None
        return cls(address=address, **data)

    @classmethod
    def update(cls, organization_id, data) -> tuple[str, int]:
        organization = cls.query.get(organization_id)
        if organization is None:
            return f"Organization with id {organization_id} not found", 404

        if address_data := data.pop("address", None):
            address_update_message, status_code = organization.address.update(address_data)
            if status_code != 200:
                return address_update_message, status_code

        for key, value in data.items():
            if hasattr(organization, key) and key != "id":
                setattr(organization, key, value)

        db.session.commit()
        return f"Successfully updated {organization.id}", 200

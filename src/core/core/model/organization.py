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

    def __init__(self, name, description=None, address=None, id=None):
        self.id = id
        self.name = name
        if description:
            self.description = description
        self.address = Address.from_dict(address) if address else None

    def to_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["address"] = self.address.to_dict() if self.address else None
        data.pop("address_id")
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
        return cls(**data)

    @classmethod
    def update(cls, organization_id, data) -> tuple[dict, int]:
        organization = cls.query.get(organization_id)
        if organization is None:
            return {"error": f"Organization {organization_id} not found"}, 404

        update_organization = cls.from_dict(data)
        organization.name = update_organization.name
        if update_organization.description:
            organization.description = update_organization.description
        if update_organization.address:
            organization.address = update_organization.address

        db.session.commit()
        return {"message": f"Successfully updated {organization.name}", "id": f"{organization.id}"}, 200

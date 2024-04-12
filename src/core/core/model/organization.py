from sqlalchemy import or_
from typing import Any

from core.managers.db_manager import db
from core.model.address import Address
from core.model.base_model import BaseModel


class Organization(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name: Any = db.Column(db.String(), nullable=False)
    description: Any = db.Column(db.String())

    address_id = db.Column(db.Integer, db.ForeignKey("address.id"))
    address: Any = db.relationship("Address", cascade="all")

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

    def to_user_dict(self):
        return {
            "id": self.id,
            "name": self.name,
        }

    @classmethod
    def get_all(cls):
        return db.session.execute(db.select(cls).order_by(db.asc(cls.name))).scalars().all()

    @classmethod
    def get_by_filter(cls, search) -> list["Organization"] | None:
        query = db.select(cls)

        if search:
            query = query.where(
                or_(
                    Organization.name.ilike(f"%{search}%"),
                    Organization.description.ilike(f"%{search}%"),
                )
            )

        query = query.order_by(db.asc(Organization.name))

        return db.session.execute(query).scalars().all()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Organization":
        return cls(**data)

    @classmethod
    def update(cls, organization_id, data) -> tuple[dict, int]:
        organization = cls.get(organization_id)
        if organization is None:
            return {"error": f"Organization {organization_id} not found"}, 404

        update_organization = cls.from_dict(data)
        organization.name = update_organization.name
        organization.description = update_organization.description
        if update_organization.address:
            organization.address = update_organization.address

        db.session.commit()
        return {"message": f"Successfully updated {organization.name}", "id": f"{organization.id}"}, 200

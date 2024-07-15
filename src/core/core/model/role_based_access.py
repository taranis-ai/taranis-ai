from enum import StrEnum, auto
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql.expression import Select, true

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.role import Role


class ItemType(StrEnum):
    OSINT_SOURCE = auto()
    OSINT_SOURCE_GROUP = auto()
    WORD_LIST = auto()
    REPORT_ITEM_TYPE = auto()
    PRODUCT_TYPE = auto()


class RoleBasedAccess(BaseModel):
    __tablename__ = "role_based_access"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    name: Mapped[str] = db.Column(db.String(64), unique=True, nullable=False)
    description: Mapped[str] = db.Column(db.String())

    item_type: Mapped = db.Column(db.Enum(ItemType))
    item_id: Mapped[str] = db.Column(db.String(64))

    roles: Mapped[list["Role"]] = relationship("Role", secondary="rbac_role", back_populates="acls")

    read_only: Mapped[bool] = db.Column(db.Boolean, default=True)
    enabled: Mapped[bool] = db.Column(db.Boolean, default=True)

    def __init__(self, name: str, description: str, item_type, item_id: str, roles=None, read_only=None, enabled=None, id=None):
        if id:
            self.id = id
        self.name = name
        self.description = description
        self.item_type = item_type
        self.item_id = item_id
        if read_only is not None:
            self.read_only = read_only
        if enabled is not None:
            self.enabled = enabled
        if roles:
            self.roles = Role.get_bulk(roles)

    @classmethod
    def is_enabled(cls) -> bool:
        query = db.select(db.exists().where(cls.enabled == true()))
        return db.session.execute(query).scalar_one()

    @classmethod
    def is_enabled_for_type(cls, item_type) -> bool:
        query = db.select(db.exists().where(cls.enabled == true()).where(cls.item_type == item_type))
        return db.session.execute(query).scalar_one()

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["roles"] = [role.id for role in self.roles if role]
        return data

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        query = db.select(cls)

        if search := filter_args.get("search"):
            query = query.where(
                or_(
                    cls.name.ilike(f"%{search}%"),
                    cls.description.ilike(f"%{search}%"),
                )
            )

        return query.order_by(db.asc(cls.name))

    @classmethod
    def update(cls, acl_id: int, data) -> tuple[dict, int]:
        acl = cls.get(acl_id)
        if not acl:
            return {"error": "ACL not found"}, 404
        for key, value in data.items():
            if not hasattr(acl, key) or key == "id":
                continue
            if key == "roles":
                acl.roles = Role.get_bulk(value)
            elif key == "item_id":
                value = str(value)
            else:
                setattr(acl, key, value)
        db.session.commit()
        return {"message": f"Succussfully updated {acl.id}", "id": acl.id}, 201


class RBACRole(BaseModel):
    __tablename__ = "rbac_role"

    acl_id = db.Column(db.Integer, db.ForeignKey("role_based_access.id", ondelete="SET NULL"), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id", ondelete="CASCADE"), primary_key=True)

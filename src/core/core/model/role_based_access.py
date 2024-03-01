from sqlalchemy import or_, Column, String, Boolean
from sqlalchemy.orm import Mapped
from typing import Any
from enum import StrEnum, auto

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

    id = db.Column(db.Integer, primary_key=True)
    name: Column[String] = db.Column(db.String(64), unique=True, nullable=False)
    description: Column[String] = db.Column(db.String())

    item_type: Column = db.Column(db.Enum(ItemType))
    item_id: Column[String] = db.Column(db.String(64))

    roles: Mapped[list[Role]] = db.relationship(Role, secondary="rbac_role", back_populates="acls")  # type: ignore

    read_only: Column[Boolean] = db.Column(db.Boolean, default=True)
    enabled: Column[Boolean] = db.Column(db.Boolean, default=True)

    def __init__(self, name, description, item_type, item_id, roles=None, read_only=None, enabled=None, id=None):
        self.id = id
        self.name = name
        self.description = description
        self.item_type = item_type
        self.item_id = str(item_id)  # type: ignore
        if read_only is not None:
            self.read_only = read_only
        if enabled is not None:
            self.enabled = enabled
        if roles:
            self.roles = [Role.get(role_id) for role_id in roles]

    @classmethod
    def is_enabled(cls) -> bool:
        return cls.query.filter_by(enabled=True).count() > 0

    @classmethod
    def is_enabled_for_type(cls, item_type) -> bool:
        return cls.query.filter_by(enabled=True).filter_by(item_type=item_type).count() > 0

    @classmethod
    def get_by_filter(cls, filter_params: dict[str, Any]):
        result = cls.query
        if search := filter_params.get("search"):
            result = result.filter(
                or_(
                    cls.name.ilike(f"%{search}%"),
                    cls.description.ilike(f"%{search}%"),
                )
            )

        return result.all(), result.count()

    @classmethod
    def get_all_json(cls, search):
        acls, count = cls.get_by_filter({"search": search})
        items = [acl.to_dict() for acl in acls]
        return {"total_count": count, "items": items}

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["roles"] = [role.id for role in self.roles if role]
        return data

    @classmethod
    def update(cls, acl_id: int, data) -> tuple[dict, int]:
        acl = cls.get(acl_id)
        if not acl:
            return {"error": "ACL not found"}, 404
        for key, value in data.items():
            if not hasattr(acl, key) or key == "id":
                continue
            elif key == "roles":
                acl.roles = [Role.get(role_id) for role_id in value]
            elif key == "item_id":
                value = str(value)
            else:
                setattr(acl, key, value)
        db.session.commit()
        return {"message": f"Succussfully updated {acl.id}", "id": acl.id}, 201


class RBACRole(BaseModel):
    __tablename__ = "rbac_role"

    acl_id = db.Column(db.Integer, db.ForeignKey("role_based_access.id", ondelete="CASCADE"), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id", ondelete="CASCADE"), primary_key=True)

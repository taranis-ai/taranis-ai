from sqlalchemy import or_
from sqlalchemy.sql.expression import Select
from sqlalchemy.orm import Mapped, relationship
import contextlib
from typing import Optional
from enum import StrEnum

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.permission import Permission


class TLPLevel(StrEnum):
    CLEAR = "clear"
    GREEN = "green"
    AMBER_STRICT = "amber+strict"
    AMBER = "amber"
    RED = "red"


class Role(BaseModel):
    __tablename__ = "role"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    name: Mapped[str] = db.Column(db.String(64), unique=True, nullable=False)
    description: Mapped[str] = db.Column(db.String())
    tlp_level: Mapped[Optional[TLPLevel]] = db.Column(db.Enum(TLPLevel), nullable=True)
    permissions: Mapped[list["Permission"]] = relationship("Permission", secondary="role_permission", back_populates="roles")
    acls = relationship("RoleBasedAccess", secondary="rbac_role")

    def __init__(self, name, description=None, tlp_level=None, permissions=None, id=None):
        if id:
            self.id = id
        self.name = name
        if description:
            self.description = description
        if tlp_level:
            self.tlp_level = tlp_level
        if permissions:
            self.permissions = Permission.get_bulk(permissions)

    @classmethod
    def filter_by_name(cls, role_name: str) -> "Role|None":
        return cls.get_first(db.select(cls).filter_by(name=role_name))

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

    def to_dict(self):
        data = super().to_dict()
        data["permissions"] = self.get_permissions()
        return data

    def to_user_dict(self):
        return {
            "id": self.id,
            "name": self.name,
        }

    def get_permissions(self):
        return [permission.id for permission in self.permissions if permission]

    def get_tlp_level(self, tlp_level: str) -> TLPLevel | None:
        with contextlib.suppress(ValueError):
            return TLPLevel(tlp_level)
        return None

    @classmethod
    def update(cls, role_id: int, data: dict) -> tuple[dict, int]:
        role = cls.get(role_id)
        if not role:
            return {"error": "Role not found"}, 404
        if name := data.get("name"):
            role.name = name
        role.description = str(data.get("description"))
        if tlp_level := data.get("tlp_level"):
            role.tlp_level = role.get_tlp_level(tlp_level)
        permissions = data.get("permissions", [])
        role.permissions = Permission.get_bulk(permissions)
        db.session.commit()
        return {"message": f"Succussfully updated {role.name}", "id": f"{role.id}"}, 201


class RolePermission(BaseModel):
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), primary_key=True)
    permission_id = db.Column(db.String, db.ForeignKey("permission.id", ondelete="SET NULL"), primary_key=True)

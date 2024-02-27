from sqlalchemy import or_
from sqlalchemy.orm import Mapped
from typing import Any
from enum import StrEnum

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.permission import Permission


class TLPLevel(StrEnum):
    WHITE = "white"
    GREEN = "green"
    AMBER = "amber"
    RED = "red"


class Role(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name: Any = db.Column(db.String(64), unique=True, nullable=False)
    description: Any = db.Column(db.String())
    tlp_level = db.Column(db.Enum(TLPLevel))
    permissions: Mapped[list[Permission]] = db.relationship(Permission, secondary="role_permission", back_populates="roles")  # type: ignore
    acls = db.relationship("RoleBasedAccess", secondary="rbac_role")  # type: ignore

    def __init__(self, name, description=None, tlp_level=None, permissions=None, id=None):
        self.id = id
        self.name = name
        if description:
            self.description = description
        if tlp_level:
            self.tlp_level = tlp_level
        if permissions:
            for permission_id in permissions:
                if permission := Permission.get(permission_id):
                    self.permissions.append(permission)

    @classmethod
    def filter_by_name(cls, role_name):
        return cls.query.filter_by(name=role_name).first()

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(Role.name)).all()

    @classmethod
    def get_by_filter(cls, search):
        query = cls.query

        if search is not None:
            query = query.filter(
                or_(
                    Role.name.ilike(f"%{search}%"),
                    Role.description.ilike(f"%{search}%"),
                )
            )

        return query.order_by(db.asc(Role.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        roles, count = cls.get_by_filter(search)
        items = [role.to_dict() for role in roles]
        return {"total_count": count, "items": items}

    @classmethod
    def load_multiple(cls, json_data: list[dict[str, Any]]) -> list["Role"]:
        return [cls.from_dict(data) for data in json_data]

    def to_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["permissions"] = self.get_permissions()
        return data

    def to_user_dict(self):
        return {
            "id": self.id,
            "name": self.name,
        }

    def get_permissions(self):
        return [permission.id for permission in self.permissions if permission]  # type: ignore

    @classmethod
    def update(cls, role_id: int, data: dict) -> tuple[dict, int]:
        role = cls.query.get(role_id)
        if role is None:
            return {"error": "Role not found"}, 404
        if name := data.get("name"):
            role.name = name
        role.description = data.get("description")
        role.tlp_level = data.get("tlp_level")
        permissions = data.get("permissions", [])
        role.permissions = [Permission.get(permission_id) for permission_id in permissions]
        db.session.commit()
        return {"message": f"Succussfully updated {role.name}", "id": f"{role.id}"}, 201


class RolePermission(BaseModel):
    role_id = db.Column(db.Integer, db.ForeignKey("role.id", ondelete="CASCADE"), primary_key=True)
    permission_id = db.Column(db.String, db.ForeignKey("permission.id", ondelete="CASCADE"), primary_key=True)

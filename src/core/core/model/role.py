from sqlalchemy import or_
from typing import Any

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.permission import Permission


class Role(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String())

    permissions = db.relationship(Permission, secondary='role_permission')

    def __init__(self, name, description, permissions, id=None):
        self.id = id
        self.name = name
        self.description = description
        self.permissions = permissions

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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Role":
        permissions = [Permission.get(permission_id) for permission_id in data.pop("permissions", [])]
        return cls(permissions=permissions, **data)

    def to_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["permissions"] = [permission.id for permission in self.permissions]
        data["tag"] = "mdi-account-arrow-right"
        return data

    def get_permissions(self):
        return {permission.id for permission in self.permissions}

    @classmethod
    def update(cls, role_id: int, data) -> tuple[str, int]:
        role = cls.query.get(role_id)
        if role is None:
            return "Role not found", 404
        permissions = [Permission.get(permission_id) for permission_id in data.pop("permissions", [])]
        role.name = data["name"]
        role.description = data["description"]
        role.permissions = permissions
        db.session.commit()
        return f"Succussfully updated {role.id}", 201


class RolePermission(BaseModel):
    role_id = db.Column(db.Integer, db.ForeignKey("role.id", ondelete="CASCADE"), primary_key=True)
    permission_id = db.Column(db.String, db.ForeignKey("permission.id", ondelete="CASCADE"), primary_key=True)

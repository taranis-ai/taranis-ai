from werkzeug.security import generate_password_hash
from typing import Any
from sqlalchemy.sql import Select
from sqlalchemy.orm import Mapped, relationship

from core.managers.db_manager import db
from core.model.role import Role
from core.model.permission import Permission
from core.model.organization import Organization

from core.model.base_model import BaseModel
from core.model.role import TLPLevel


class User(BaseModel):
    __tablename__ = "user"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    username: Mapped[str] = db.Column(db.String(64), unique=True, nullable=False)
    name: Mapped[str] = db.Column(db.String(), nullable=False)
    password: Mapped[str] = db.Column(db.String(), nullable=True)

    organization_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("organization.id"))
    organization: Mapped[Organization] = relationship(Organization)

    roles: Mapped[list[Role]] = relationship(Role, secondary="user_role", cascade="all, delete")
    permissions: Mapped[list[Permission]] = relationship(Permission, secondary="user_permission", cascade="all, delete")

    profile_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("user_profile.id", ondelete="CASCADE"))
    profile: Mapped["UserProfile"] = relationship("UserProfile", cascade="all, delete")

    def __init__(self, username: str, name: str, organization: int, roles: list[int], permissions: list[str], password=None, id=None):
        if id:
            self.id = id
        self.username = username
        self.name = name
        if not password:
            raise ValueError("Password is required")
        self.password = generate_password_hash(password)
        self.organization = Organization.get(organization)
        self.roles = [Role.get(role) for role in roles]
        self.permissions = [Permission.get(permission) for permission in permissions]
        self.profile = UserProfile(id=id)

    @classmethod
    def find_by_name(cls, username: str) -> "User":
        return cls.query.filter_by(username=username).first()

    @classmethod
    def find_by_role(cls, role_id: int) -> "User":
        return cls.query.join(Role, Role.id == role_id).all()

    @classmethod
    def find_by_role_name(cls, role_name: str) -> "User":
        return cls.query.join(Role, Role.name == role_name).all()

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(User.name)).all()

    def to_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns if c.name != "password"}
        data["organization"] = data.pop("organization_id")
        data["roles"] = [role.id for role in self.roles if role]
        data["permissions"] = [permission.id for permission in self.permissions if permission]
        return data

    def to_detail_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "username": self.username,
            "organization": self.organization.to_user_dict(),
            "roles": [role.to_user_dict() for role in self.roles if role],
            "permissions": self.get_permissions(),
            "profile": self.profile.to_dict(),
        }

    @classmethod
    def add(cls, data) -> "User":
        item = cls.from_dict(data)
        db.session.add(item)
        db.session.commit()
        return item

    @classmethod
    def update(cls, user_id, data) -> tuple[dict[str, Any], int]:
        user = cls.get(user_id)
        if not user:
            return {"error": f"User {user_id} not found"}, 404
        data.pop("id", None)
        if update_organization := data.pop("organization", None):
            user.organization = Organization.get(update_organization)
        if not (update_roles := data.pop("roles", None)):
            user.roles = data.get("roles", [])
        else:
            user.roles = [Role.get(role_id) for role_id in update_roles]
        if not (update_permissions := data.pop("permissions", None)):
            user.permissions = data.get("permissions", [])
        else:
            user.permissions = [Permission.get(permission_id) for permission_id in update_permissions]
        if update_password := data.pop("password", None):
            user.password = generate_password_hash(update_password)
        if update_name := data.pop("name", None):
            user.name = update_name
        if update_username := data.pop("username", None):
            user.username = update_username

        db.session.commit()
        return {"message": f"User {user_id} updated", "id": user_id}, 200

    def get_permissions(self):
        all_permissions = {permission.id for permission in self.permissions if permission}

        for role in self.roles:
            if role:
                all_permissions.update(role.get_permissions())
        return list(all_permissions)

    def get_roles(self):
        return [role.id for role in self.roles]

    def get_highest_tlp(self) -> TLPLevel | None:
        highest_tlp = None
        for role in self.roles:
            if tlp_level := role.tlp_level:
                tlp_level_enum = TLPLevel(tlp_level)
                if highest_tlp is None or tlp_level_enum > highest_tlp:
                    highest_tlp = tlp_level_enum
        return highest_tlp

    def get_current_organization_name(self):
        return self.organization.name if self.organization else ""

    def get_profile_json(self) -> tuple[dict, int]:
        return self.profile.to_dict(), 200

    @classmethod
    def update_profile(cls, user: "User", data) -> tuple[dict, int]:
        return user.profile.update(data)

    @classmethod
    def delete(cls, id: int) -> tuple[dict[str, Any], int]:
        result = super().delete(id)
        UserProfile.delete(id)
        return result

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        query = db.select(cls)

        if organization := filter_args.get("organization"):
            query = query.where(User.organization_id == organization.id)

        if search := filter_args.get("search"):
            query = query.filter(db.or_(User.name.ilike(f"%{search}%"), User.username.ilike(f"%{search}%")))

        return query.order_by(db.asc(User.name))


class UserRole(BaseModel):
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id", ondelete="CASCADE"), primary_key=True)


class UserPermission(BaseModel):
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    permission_id = db.Column(db.String, db.ForeignKey("permission.id", ondelete="CASCADE"), primary_key=True)


class UserProfile(BaseModel):
    id = db.Column(db.Integer, primary_key=True)

    dark_theme = db.Column(db.Boolean, default=False)
    split_view = db.Column(db.Boolean, default=False)
    compact_view = db.Column(db.Boolean, default=False)
    show_charts = db.Column(db.Boolean, default=False)

    hotkeys: Any = db.Column(db.JSON)
    language = db.Column(db.String(2), default="en")

    def __init__(self, dark_theme=False, hotkeys=None, split_view=None, compact_view=None, show_charts=None, language="en", id=None):
        self.id = id
        self.dark_theme = dark_theme
        self.split_view = split_view
        self.compact_view = compact_view
        self.show_charts = show_charts
        self.hotkeys = hotkeys or {}
        self.language = language

    def to_dict(self):
        return {
            "split_view": self.split_view,
            "compact_view": self.compact_view,
            "show_charts": self.show_charts,
            "dark_theme": self.dark_theme,
            "hotkeys": self.hotkeys,
            "language": self.language,
        }

    def update(self, data) -> tuple[dict[str, Any], int]:
        self.dark_theme = data.pop("dark_theme", self.dark_theme)
        self.language = data.pop("language", self.language)
        self.split_view = data.pop("split_view", self.split_view)
        self.compact_view = data.pop("compact_view", self.compact_view)
        self.show_charts = data.pop("show_charts", self.show_charts)
        self.hotkeys = data.pop("hotkeys", self.hotkeys)

        db.session.commit()
        return {"message": "UserProfile updated", "id": f"{self.id}"}, 200

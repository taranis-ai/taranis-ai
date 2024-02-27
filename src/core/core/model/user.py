from sqlalchemy import or_
from werkzeug.security import generate_password_hash
from typing import Any

from core.managers.db_manager import db
from core.model.role import Role
from core.model.permission import Permission
from core.model.organization import Organization

from core.model.base_model import BaseModel
from core.managers.log_manager import logger


class User(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    username: Any = db.Column(db.String(64), unique=True, nullable=False)
    name: Any = db.Column(db.String(), nullable=False)
    password: Any = db.Column(db.String(), nullable=True)

    organization_id = db.Column(db.Integer, db.ForeignKey("organization.id"))
    organization: Any = db.relationship("Organization")

    roles: Any = db.relationship(Role, secondary="user_role", cascade="all, delete")
    permissions: Any = db.relationship(Permission, secondary="user_permission", cascade="all, delete")

    profile_id = db.Column(db.Integer, db.ForeignKey("user_profile.id", ondelete="CASCADE"))
    profile = db.relationship("UserProfile", cascade="all, delete")

    def __init__(self, username, name, organization, roles, permissions, password=None, id=None):
        self.id = id
        self.username = username
        self.name = name
        if password:
            self.password = generate_password_hash(password)
        self.organization = Organization.get(organization)
        self.roles = [Role.get(role) for role in roles]
        self.permissions = [Permission.get(permission) for permission in permissions]
        self.profile = UserProfile(id=id)

    @classmethod
    def find_by_name(cls, username: str) -> "User":
        return cls.query.filter_by(username=username).first()

    @classmethod
    def find_by_id(cls, user_id) -> "User":
        return cls.query.get(user_id)

    @classmethod
    def find_by_role(cls, role_id: int) -> "User":
        return cls.query.join(Role, Role.id == role_id).all()

    @classmethod
    def find_by_role_name(cls, role_name: str) -> "User":
        return cls.query.join(Role, Role.name == role_name).all()

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(User.name)).all()

    @classmethod
    def get_by_filter(cls, search, organization):
        query = cls.query

        if organization:
            query = query.filter(User.organization_id == organization.id)

        if search is not None:
            query = query.filter(
                or_(
                    User.name.ilike(f"%{search}%"),
                    User.username.ilike(f"%{search}%"),
                )
            )

        return query.order_by(db.asc(User.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search=None):
        users, count = cls.get_by_filter(search, None)
        items = [user.to_dict() for user in users]
        return {"total_count": count, "items": items}

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
        if not item.password:
            raise ValueError("Password is required")
        db.session.add(item)
        db.session.commit()
        return item

    @classmethod
    def update(cls, user_id, data) -> tuple[dict[str, Any], int]:
        user = cls.get(user_id)
        if not user:
            return {"error": f"User {user_id} not found"}, 404
        data.pop("id", None)
        data.pop("tag", None)
        if update_organization := data.pop("organization", None):
            user.organization = Organization.get(update_organization)
        if update_profile := data.pop("profile_id", None):
            user.profile = UserProfile.get(update_profile)
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

    def get_current_organization_name(self):
        return self.organization.name if self.organization else ""

    def get_profile_json(self) -> tuple[dict, int]:
        return self.profile.to_dict(), 200

    @classmethod
    def update_profile(cls, user, data):
        logger.debug(user.profile.from_dict(data))
        user.profile = user.profile.from_dict(data)

        db.session.commit()
        return user.profile.to_dict(), 200

    @classmethod
    def delete(cls, id: int) -> tuple[dict[str, Any], int]:
        result = super().delete(id)
        UserProfile.delete(id)
        return result


class UserRole(BaseModel):
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id", ondelete="CASCADE"), primary_key=True)


class UserPermission(BaseModel):
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    permission_id = db.Column(db.String, db.ForeignKey("permission.id", ondelete="CASCADE"), primary_key=True)


class UserProfile(BaseModel):
    id = db.Column(db.Integer, primary_key=True)

    spellcheck = db.Column(db.Boolean, default=True)
    dark_theme = db.Column(db.Boolean, default=False)

    hotkeys: Any = db.relationship("Hotkey", cascade="all, delete-orphan")
    language = db.Column(db.String(2), default="en")

    def __init__(self, spellcheck=True, dark_theme=False, hotkeys=None, language="en", id=None):
        self.id = id
        self.spellcheck = spellcheck
        self.dark_theme = dark_theme
        self.hotkeys = hotkeys or []
        self.language = language

    @classmethod
    def from_dict(cls, data: dict):
        hotkeys = [Hotkey.from_dict(hotkey) for hotkey in data["hotkeys"]]
        return cls(data["spellcheck"], data["dark_theme"], hotkeys, data["language"])

    def to_dict(self):
        return {
            "spellcheck": self.spellcheck,
            "dark_theme": self.dark_theme,
            "hotkeys": [hotkey.to_dict() for hotkey in self.hotkeys],
            "language": self.language,
        }


class Hotkey(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    key_code = db.Column(db.Integer)
    key = db.Column(db.String)
    alias = db.Column(db.String)

    user_profile_id = db.Column(db.Integer, db.ForeignKey("user_profile.id", ondelete="CASCADE"))

    def __init__(self, key_code, key, alias, id=None):
        self.id = id
        self.key_code = key_code
        self.key = key
        self.alias = alias

    @classmethod
    def from_dict(cls, data: dict) -> "Hotkey":
        logger.debug(data)
        return cls(data["key_code"], data["key"], data["alias"])

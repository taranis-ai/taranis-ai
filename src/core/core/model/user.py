import json
import secrets
from copy import deepcopy
from typing import Any, Sequence

from models.user import ProfileSettings, UserProfile
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import Select
from werkzeug.security import generate_password_hash

from core.log import logger
from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.organization import Organization
from core.model.role import Role, TLPLevel


PROFILE_TEMPLATE: dict[str, Any] = ProfileSettings().model_dump(mode="json")


class User(BaseModel):
    __tablename__ = "user"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    username: Mapped[str] = db.Column(db.String(64), unique=True, nullable=False)
    name: Mapped[str] = db.Column(db.String(), nullable=False)
    password: Mapped[str] = db.Column(db.String(), nullable=True)

    organization_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("organization.id"))
    organization: Mapped["Organization"] = relationship("Organization")

    roles: Mapped[list["Role"]] = relationship("Role", secondary="user_role")
    profile: Mapped[dict[str, Any]] = db.Column(db.JSON)

    def __init__(self, username: str, name: str, organization: int, roles: list[int], password=None, id=None):
        if id:
            self.id = id
        self.username = username
        self.name = name
        if password:
            self.password = generate_password_hash(password)
        if org := Organization.get(organization):
            self.organization = org
        self.roles = Role.get_bulk(roles)
        self.profile = deepcopy(PROFILE_TEMPLATE)

    @classmethod
    def find_by_name(cls, username: str) -> "User|None":
        return cls.get_first(db.select(cls).filter_by(username=username))

    @classmethod
    def find_by_role(cls, role_id: int) -> "Sequence[User]":
        return cls.get_filtered(db.select(cls).join(Role, Role.id == role_id)) or []

    @classmethod
    def find_by_role_name(cls, role_name: str) -> "Sequence[User]":
        return cls.get_filtered(db.select(cls).join(Role, Role.name == role_name)) or []

    def to_dict(self):
        data = super().to_dict()
        del data["password"]
        data["organization"] = data.pop("organization_id")
        data["roles"] = [role.id for role in self.roles if role]
        data["permissions"] = self.get_permissions()
        return data

    def to_detail_dict(self):
        return self.to_user_profile().model_dump(mode="json")

    def to_user_profile(self) -> UserProfile:
        return UserProfile(
            id=self.id,
            username=self.username,
            name=self.name,
            organization=({"id": self.organization.id, "name": self.organization.name} if self.organization else None),
            roles=[{"id": r.id, "name": r.name} for r in self.roles if r],
            permissions=self.get_permissions(),
            profile=ProfileSettings.model_validate(self.profile or {}),
        )

    @classmethod
    def get_for_api(cls, item_id) -> tuple[dict[str, Any], int]:
        if item := cls.get(item_id):
            return item.to_detail_dict(), 200
        return {"error": f"{cls.__name__} {item_id} not found"}, 404

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
        if organization := data.pop("organization", None):
            if update_org := Organization.get(organization):
                user.organization = update_org
        if (roles := data.pop("roles", None)) is not None:
            user.roles = Role.get_bulk(roles)
        if update_password := data.pop("password", None):
            user.password = generate_password_hash(update_password)
        if update_name := data.pop("name", None):
            user.name = update_name
        if update_username := data.pop("username", None):
            user.username = update_username

        db.session.commit()
        return {"message": f"User {user_id} updated", "id": user_id}, 200

    def get_permissions(self) -> list[str]:
        permissions = {permission for role in self.roles if role for permission in role.get_permissions()}
        return list(permissions)

    def change_password(self, new_password: str):
        self.password = generate_password_hash(new_password)
        db.session.commit()

    def get_roles(self):
        return [role.id for role in self.roles]

    def get_highest_tlp(self) -> TLPLevel:
        highest_tlp = TLPLevel.CLEAR
        for role in self.roles:
            if tlp_level := role.tlp_level:
                highest_tlp = TLPLevel.get_most_restrictive_tlp([highest_tlp, tlp_level])
        return highest_tlp

    def get_current_organization_name(self):
        return self.organization.name if self.organization else ""

    @classmethod
    def get_filter_query(cls, filter_args: dict[str, Any]) -> Select:
        query = db.select(cls)

        if organization := filter_args.get("organization"):
            query = query.where(User.organization_id == organization.id)

        if search := filter_args.get("search"):
            query = query.filter(db.or_(User.name.ilike(f"%{search}%"), User.username.ilike(f"%{search}%")))

        return query

    @classmethod
    def default_sort_column(cls) -> str:
        return "name_asc"

    @classmethod
    def parse_json(cls, content) -> list | None:
        file_content = json.loads(content)
        return cls.load_json_content(content=file_content)

    @classmethod
    def load_json_content(cls, content) -> list:
        if content.get("version") != 1:
            raise ValueError("Invalid JSON file")
        if not content.get("data"):
            raise ValueError("No data found")
        return content["data"]

    def to_export_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "username": self.username,
        }

    def get_profile(self) -> dict:
        return ProfileSettings.model_validate(self.profile or {}).model_dump(mode="json")

    @classmethod
    def update_profile(cls, user: "User", data: dict) -> tuple[dict, int]:
        logger.debug(f"Updating profile for user {user.username} with data: {data}")
        merged = {**(user.profile or {}), **data}

        validated = ProfileSettings.model_validate(merged)
        user.profile = validated.model_dump(mode="json")

        db.session.commit()
        return {"message": "Profile updated", "id": user.id, "user_profile": user.get_profile()}, 200

    @classmethod
    def export(cls, user_ids=None) -> bytes:
        query = db.select(cls)
        if user_ids:
            query = query.filter(cls.id.in_(user_ids))

        data = cls.get_filtered(query)
        export_data = {"version": 1, "data": [user.to_export_dict() for user in data]} if data else {}
        return json.dumps(export_data).encode("utf-8")

    @classmethod
    def import_users(cls, user_list: list) -> list:
        result = []
        for user in user_list:
            if cls.find_by_name(user["username"]):
                logger.warning(f"User {user['username']} already exists")
                continue
            user["password"] = secrets.token_urlsafe(16)
            cls.add(user)
            result.append({"username": user["username"], "password": user["password"]})
        return result


class UserRole(BaseModel):
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    role_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("role.id", ondelete="SET NULL"), primary_key=True)

    @classmethod
    def has_assigned_user(cls, role_id: int) -> bool:
        return db.session.execute(db.select(db.exists().where(UserRole.role_id == role_id))).scalar_one()

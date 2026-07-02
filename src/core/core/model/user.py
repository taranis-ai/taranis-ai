import json
from datetime import datetime
from typing import Any, Sequence

from models.user import (
    ADMIN_ADVANCED_TOUR_ID,
    ADMIN_WELCOME_TOUR_ID,
    ONBOARDING_COMPLETED_STATUS,
    ONBOARDING_DISMISSED_STATUS,
    ONBOARDING_SCOPE_GLOBAL,
    ONBOARDING_SCOPE_USER,
    USER_PRODUCT_OVERVIEW_TASK_ID,
    OnboardingTask,
    ProfileSettings,
    UserProfile,
)
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import Select
from werkzeug.security import generate_password_hash

from core.log import logger
from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel
from core.model.organization import Organization
from core.model.role import Role, TLPLevel
from core.model.settings import Settings


PROFILE_TEMPLATE: dict[str, Any] = ProfileSettings().model_dump(mode="json")
REMOVED_PROFILE_KEYS = frozenset({"assess_default_filters"})
ADMIN_ONBOARDING_TASK_IDS = (ADMIN_WELCOME_TOUR_ID, ADMIN_ADVANCED_TOUR_ID)
USER_PRODUCT_OVERVIEW_PERMISSIONS = frozenset({"ASSESS_ACCESS", "ANALYZE_ACCESS", "PUBLISH_ACCESS"})


class User(BaseModel):
    __tablename__ = "user"

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    username: Mapped[str] = db.Column(db.String(64), unique=True, nullable=False)
    name: Mapped[str] = db.Column(db.String(), nullable=False)
    password: Mapped[str] = db.Column(db.String(), nullable=True)
    last_login: Mapped[datetime | None] = db.Column(db.DateTime, nullable=True)

    organization_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("organization.id"))
    organization: Mapped["Organization"] = relationship("Organization")

    roles: Mapped[list["Role"]] = relationship("Role", secondary="user_role")
    profile: Mapped[dict[str, Any]] = db.Column(db.JSON)

    def __init__(
        self,
        username: str,
        name: str,
        organization: str | dict[str, str] | None,
        roles: list[str],
        password=None,
        id=None,
        profile: dict[str, Any] | None = None,
    ):
        self.id = self.normalize_uuid_id(id)
        self.username = username
        self.name = name
        if password:
            self.password = generate_password_hash(password)
        organization_id = organization.get("id") if isinstance(organization, dict) else organization
        if organization_id is not None and (org := Organization.get(organization_id)):
            self.organization = org
        self.roles = Role.get_bulk(roles)
        profile_payload = dict(profile or {})
        if not profile_payload.get("timezone"):
            profile_payload["timezone"] = Settings.get_settings().get("default_timezone") or "UTC"
        self.profile = ProfileSettings.model_validate(profile_payload).model_dump(mode="json")

    @classmethod
    def find_by_name(cls, username: str) -> "User|None":
        return cls.get_first(db.select(cls).filter_by(username=username))

    @classmethod
    def find_by_role(cls, role_id: str) -> "Sequence[User]":
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

    @staticmethod
    def _is_onboarding_task_finished(status: Any) -> bool:
        return status in {ONBOARDING_COMPLETED_STATUS, ONBOARDING_DISMISSED_STATUS}

    @staticmethod
    def _has_any_permission(permissions: Sequence[str], required_permissions: frozenset[str]) -> bool:
        permission_set = set(permissions)
        return "ALL" in permission_set or bool(permission_set.intersection(required_permissions))

    @classmethod
    def _pending_global_onboarding_tasks(cls, profile: ProfileSettings, permissions: Sequence[str]) -> list[OnboardingTask]:
        if not cls._has_any_permission(permissions, frozenset({"ADMIN_OPERATIONS"})):
            return []

        return [
            OnboardingTask(id=task_id, scope=ONBOARDING_SCOPE_GLOBAL)
            for task_id in ADMIN_ONBOARDING_TASK_IDS
            if not cls._is_onboarding_task_finished(profile.onboarding_tasks.get(task_id))
        ]

    @classmethod
    def _pending_user_onboarding_tasks(cls, profile: ProfileSettings, permissions: Sequence[str]) -> list[OnboardingTask]:
        if not cls._has_any_permission(permissions, USER_PRODUCT_OVERVIEW_PERMISSIONS):
            return []

        if cls._is_onboarding_task_finished(profile.onboarding_tasks.get(USER_PRODUCT_OVERVIEW_TASK_ID)):
            return []

        return [OnboardingTask(id=USER_PRODUCT_OVERVIEW_TASK_ID, scope=ONBOARDING_SCOPE_USER)]

    @classmethod
    def _pending_onboarding_tasks(cls, profile: ProfileSettings, permissions: Sequence[str]) -> list[OnboardingTask]:
        return [
            *cls._pending_global_onboarding_tasks(profile, permissions),
            *cls._pending_user_onboarding_tasks(profile, permissions),
        ]

    @staticmethod
    def _clean_profile_payload(profile: dict[str, Any] | None) -> dict[str, Any]:
        return {key: value for key, value in (profile or {}).items() if key not in REMOVED_PROFILE_KEYS}

    def to_user_profile(self) -> UserProfile:
        permissions = self.get_permissions()
        profile = ProfileSettings.model_validate(self._clean_profile_payload(self.profile))
        return UserProfile(
            id=self.id,
            username=self.username,
            name=self.name,
            last_login=self.last_login,
            organization=({"id": self.organization.id, "name": self.organization.name} if self.organization else None),
            roles=[{"id": r.id, "name": r.name} for r in self.roles if r],
            permissions=permissions,
            profile=profile,
            effective_timezone=profile.timezone or "UTC",
            pending_onboarding_tasks=self._pending_onboarding_tasks(profile, permissions),
        )

    def mark_last_login(self) -> None:
        self.last_login = self.utcnow()
        db.session.commit()

    @classmethod
    def get_for_api(cls, item_id) -> tuple[dict[str, Any], int]:
        if item := cls.get(item_id):
            return item.to_detail_dict(), 200
        return {"error": f"{cls.__name__} not found"}, 404

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
            return {"error": "User not found"}, 404
        data.pop("id", None)
        if organization := data.pop("organization", None):
            if isinstance(organization, dict):
                organization = organization.get("id") or organization.get("name")
            if organization is not None and (update_org := Organization.get(organization)):
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
        return {"message": "User updated", "id": user.id}, 200

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
        return ProfileSettings.model_validate(self._clean_profile_payload(self.profile)).model_dump(mode="json")

    @classmethod
    def update_profile(cls, user: "User", data: dict) -> tuple[dict, int]:
        logger.debug(f"Updating profile for user {user.username} with data: {data}")
        merged = {**cls._clean_profile_payload(user.profile), **cls._clean_profile_payload(data)}

        try:
            validated = ProfileSettings.model_validate(merged)
        except ValidationError as exc:
            return ProfileSettings.validation_error_response(exc, prefix="Invalid profile settings"), 400

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

    @staticmethod
    def _skipped_import_user(username: Any, reason: str) -> dict[str, str]:
        return {"username": "" if username is None else str(username).strip(), "reason": reason}

    @staticmethod
    def _import_message(imported_count: int, skipped_count: int) -> str:
        return f"Imported {imported_count} user(s); skipped {skipped_count} user(s)"

    @classmethod
    def _sanity_check_import_user(cls, user: Any, seen_usernames: set[str]) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
        if not isinstance(user, dict):
            logger.warning("Skipped user import: item is not a dict")
            return None, cls._skipped_import_user(None, "invalid item type")

        username = user.get("username")
        if not isinstance(username, str) or not username.strip():
            logger.warning("Skipped user import: missing or invalid username")
            return None, cls._skipped_import_user(username, "missing or invalid username")

        name = user.get("name")
        if not isinstance(name, str):
            logger.warning(f"Skipped user import for {username}: missing or invalid name")
            return None, cls._skipped_import_user(username, "missing or invalid name")

        username = username.strip()
        if cls.find_by_name(username):
            logger.warning(f"User {username} already exists")
            return None, cls._skipped_import_user(username, "user already exists")
        if username in seen_usernames:
            logger.warning(f"Skipped user import for {username}: duplicate username in import file")
            return None, cls._skipped_import_user(username, "duplicate username in import file")

        import_user = dict(user)
        import_user["username"] = username
        import_user.setdefault("organization", None)
        import_user.setdefault("roles", [])
        return import_user, None

    @classmethod
    def import_users(cls, user_list: list) -> dict[str, Any]:
        imported_users = []
        skipped_users = []
        staged_users = []
        seen_usernames = set()
        for user in user_list:
            import_user, skipped_user = cls._sanity_check_import_user(user, seen_usernames)
            if skipped_user is not None:
                skipped_users.append(skipped_user)
                continue
            if import_user is None:
                continue
            username = import_user["username"]
            try:
                staged_users.append((username, cls.from_dict(import_user)))
                seen_usernames.add(username)
            except (SQLAlchemyError, TypeError, ValueError, ValidationError) as exc:
                logger.warning(f"Skipped user import for {username}: invalid user data ({exc})")
                skipped_users.append(cls._skipped_import_user(username, "invalid user data"))
                continue

        try:
            db.session.add_all([user for _, user in staged_users])
            db.session.commit()
        except SQLAlchemyError as exc:
            db.session.rollback()
            logger.warning(f"User import batch failed; rolled back staged users ({exc})")
            skipped_users.extend(cls._skipped_import_user(username, "invalid user data") for username, _ in staged_users)
        else:
            imported_users = [{"username": username} for username, _ in staged_users]

        imported_count = len(imported_users)
        skipped_count = len(skipped_users)
        return {
            "users": imported_users,
            "count": imported_count,
            "skipped_users": skipped_users,
            "skipped_count": skipped_count,
            "message": cls._import_message(imported_count, skipped_count),
        }


class UserRole(BaseModel):
    user_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("user.id"), primary_key=True)
    role_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("role.id", ondelete="SET NULL"), primary_key=True)

    @classmethod
    def has_assigned_user(cls, role_id: str) -> bool:
        return db.session.execute(db.select(db.exists().where(UserRole.role_id == role_id))).scalar_one()

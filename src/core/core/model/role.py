import contextlib
from enum import StrEnum
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql.expression import Select

from core.log import logger
from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel
from core.model.permission import Permission


TLP_ACCESSIBLE_NAMES = {
    "RED": ["RED", "AMBER_STRICT", "AMBER", "GREEN", "CLEAR"],
    "AMBER_STRICT": ["AMBER_STRICT", "AMBER", "GREEN", "CLEAR"],
    "AMBER": ["AMBER", "GREEN", "CLEAR"],
    "GREEN": ["GREEN", "CLEAR"],
    "CLEAR": ["CLEAR"],
}


class TLPLevel(StrEnum):
    CLEAR = "clear"
    GREEN = "green"
    AMBER_STRICT = "amber+strict"
    AMBER = "amber"
    RED = "red"

    def get_accessible_levels(self) -> list[str]:
        """
        Return the list of TLPLevel members this level can access.
        """
        names = TLP_ACCESSIBLE_NAMES.get(self.name, [])
        return [type(self).__members__[name].value for name in names]

    @classmethod
    def get_most_restrictive_tlp(cls, tlp_levels: list["TLPLevel"]) -> "TLPLevel":
        """
        Get the most restrictive TLP level from a list of TLP levels.
        If the list is empty, return the default TLP level (CLEAR).
        """
        if not tlp_levels:
            return cls.CLEAR

        provided = {tlp.name for tlp in tlp_levels}

        return next(
            (cls.__members__[level_name] for level_name in TLP_ACCESSIBLE_NAMES if level_name in provided),
            cls.CLEAR,
        )

    @classmethod
    def get_tlp_level(cls, tlp_level: str) -> "TLPLevel | None":
        with contextlib.suppress(ValueError):
            return TLPLevel(tlp_level)
        return None


class Role(BaseModel):
    __tablename__ = "role"

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    name: Mapped[str] = db.Column(db.String(64), unique=True, nullable=False)
    description: Mapped[str] = db.Column(db.String())
    tlp_level: Mapped[Optional[TLPLevel]] = db.Column(db.Enum(TLPLevel), nullable=False, default=TLPLevel.CLEAR)
    permissions: Mapped[list["Permission"]] = relationship("Permission", secondary="role_permission", back_populates="roles")
    acls = relationship("RoleBasedAccess", secondary="rbac_role")

    def __init__(self, name, description=None, tlp_level=None, permissions=None, id=None):
        self.id = self.normalize_uuid_id(id)
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

        return query

    @classmethod
    def default_sort_column(cls) -> str:
        return "name_asc"

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
        return [permission.code for permission in self.permissions if permission]

    @classmethod
    def update(cls, role_id: str, data: dict) -> tuple[dict, int]:
        logger.debug(f"Updating role with ID {role_id} with data: {data}")
        role = cls.get(role_id)
        if not role:
            return {"error": "Role not found"}, 404
        if name := data.get("name"):
            role.name = name
        role.description = str(data.get("description"))
        if tlp_level := data.get("tlp_level"):
            role.tlp_level = TLPLevel.get_tlp_level(tlp_level)
        permissions = data.get("permissions", [])
        role.permissions = Permission.get_bulk(permissions)
        db.session.commit()
        return {"message": "Role updated", "id": f"{role.id}"}, 201

    @classmethod
    def delete(cls, role_id: str) -> tuple[dict[str, str], int]:
        if item := cls.get(role_id):
            db.session.delete(item)
            db.session.commit()
            return {"message": f"{cls.__name__} deleted"}, 200
        logger.warning(f"{cls.__name__} {role_id} not found")
        return {"error": f"{cls.__name__} not found"}, 404


class RolePermission(BaseModel):
    role_id = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("role.id"), primary_key=True)
    permission_id = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("permission.id", ondelete="SET NULL"), primary_key=True)

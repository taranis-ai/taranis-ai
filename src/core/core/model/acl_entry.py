from sqlalchemy import or_, and_
from flask_sqlalchemy import query
from typing import Any
from enum import Enum, auto

from core.managers.db_manager import db
from core.model.role import Role
from core.model.user import User
from core.model.base_model import BaseModel


class ItemType(Enum):
    OSINT_SOURCE = auto()
    OSINT_SOURCE_GROUP = auto()
    WORD_LIST = auto()
    REPORT_ITEM = auto()
    REPORT_ITEM_TYPE = auto()
    PRODUCT_TYPE = auto()
    DELEGATION = auto()


class ACLEntry(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String())

    item_type = db.Column(db.Enum(ItemType))
    item_id = db.Column(db.String(64))

    everyone = db.Column(db.Boolean, default=True)
    users = db.relationship("User", secondary="acl_entry_user")
    roles = db.relationship("Role", secondary="acl_entry_role")

    see = db.Column(db.Boolean)
    access = db.Column(db.Boolean)
    modify = db.Column(db.Boolean)

    def __init__(
        self, name, description, item_type, item_id, everyone=True, see=False, access=False, modify=False, users=None, roles=None, id=None
    ):
        self.id = id
        self.name = name
        self.description = description
        self.item_type = item_type
        self.item_id = item_id
        self.everyone = everyone
        self.see = see
        self.access = access
        self.modify = modify
        self.users = [User.find_by_id(user.id) for user in users] if users else []
        self.roles = [Role.get(role.id) for role in roles] if roles else []

    @classmethod
    def has_rows(cls) -> bool:
        return cls.query.count() > 0

    @classmethod
    def get_by_filter(cls, filter_params: dict[str, Any]):
        query = cls.query

        if search := filter_params.get("search"):
            query = query.filter(
                or_(
                    cls.name.ilike(f"%{search}%"),
                    cls.description.ilike(f"%{search}%"),
                )
            )

        return query.all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        acls, count = cls.get_by_filter({"search": search})
        items = [acl.to_dict() for acl in acls]
        return {"total_count": count, "items": items}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ACLEntry":
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["roles"] = [role.id for role in self.roles if role]
        data["users"] = [user.id for user in self.users if user]
        return data

    @classmethod
    def update(cls, acl_id: int, data) -> tuple[dict, int]:
        acl = cls.get(acl_id)
        if not acl:
            return {"error": "ACL not found"}, 404
        for key, value in data.items():
            if hasattr(acl, key) and key != "id":
                setattr(acl, key, value)
        db.session.commit()
        return {"message": f"Succussfully updated {acl.id}", "id": acl.id}, 201

    @classmethod
    def apply_query(cls, query: query.Query, user: User, see: bool, access: bool, modify: bool) -> query.Query:
        roles = [role.id for role in user.roles if role]

        query = query.outerjoin(
            ACLEntryUser,
            and_(
                ACLEntryUser.acl_entry_id == ACLEntry.id,
                ACLEntryUser.user_id == user.id,
            ),
        )

        query = query.outerjoin(ACLEntryRole, ACLEntryRole.acl_entry_id == ACLEntry.id)

        if see:
            return query.filter(
                or_(
                    ACLEntry.id is not None,
                    and_(
                        ACLEntry.see,
                        or_(
                            ACLEntry.everyone,
                            ACLEntryUser.user_id == user.id,
                            ACLEntryRole.role_id.in_(roles),
                        ),
                    ),
                )
            )

        if access:
            return query.filter(
                or_(
                    ACLEntry.id is not None,
                    and_(
                        ACLEntry.access,
                        or_(
                            ACLEntry.everyone,
                            ACLEntryUser.user_id == user.id,
                            ACLEntryRole.role_id.in_(roles),
                        ),
                    ),
                )
            )

        if modify:
            return query.filter(
                or_(
                    ACLEntry.id is not None,
                    and_(
                        ACLEntry.modify,
                        or_(
                            ACLEntry.everyone,
                            ACLEntryUser.user_id == user.id,
                            ACLEntryRole.role_id.in_(roles),
                        ),
                    ),
                )
            )

        return query.filter(
            or_(
                ACLEntry.id is not None,
                ACLEntry.everyone,
                ACLEntryUser.user_id == user.id,
                ACLEntryRole.role_id.in_(roles),
            )
        )


class ACLEntryUser(BaseModel):
    acl_entry_id = db.Column(db.Integer, db.ForeignKey("acl_entry.id"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)


class ACLEntryRole(BaseModel):
    acl_entry_id = db.Column(db.Integer, db.ForeignKey("acl_entry.id"), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), primary_key=True)

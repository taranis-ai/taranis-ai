from sqlalchemy import func, or_, orm, and_
from marshmallow import fields, post_load
from flask_sqlalchemy import BaseQuery

from core.managers.db_manager import db
from core.model.role import Role
from core.model.user import User
from shared.schema.role import RoleIdSchema
from shared.schema.user import UserIdSchema
from shared.schema.acl_entry import ACLEntrySchema, ACLEntryPresentationSchema, ItemType


class NewACLEntrySchema(ACLEntrySchema):
    users = fields.Nested(UserIdSchema, many=True)
    roles = fields.Nested(RoleIdSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        return ACLEntry(**data)


class ACLEntry(db.Model):
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

    def __init__(self, id, name, description, item_type, item_id, everyone, users, see, access, modify, roles):
        self.id = None
        self.name = name
        self.description = description
        self.item_type = item_type
        self.item_id = item_id
        self.everyone = everyone
        self.see = see
        self.access = access
        self.modify = modify
        self.users = [User.find_by_id(user.id) for user in users]
        self.roles = [Role.find(role.id) for role in roles]
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-lock-check"

    @classmethod
    def find(cls, id):
        return cls.query.get(id)

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(ACLEntry.name)).all()

    @classmethod
    def get(cls, search):
        query = cls.query

        if search is not None:
            search_string = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(ACLEntry.name).like(search_string),
                    func.lower(ACLEntry.description).like(search_string),
                )
            )

        return query.order_by(db.asc(ACLEntry.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        acls, count = cls.get(search)
        acl_schema = ACLEntryPresentationSchema(many=True)
        return {"total_count": count, "items": acl_schema.dump(acls)}

    @classmethod
    def add_new(cls, data):
        new_acl_schema = NewACLEntrySchema()
        acl = new_acl_schema.load(data)
        db.session.add(acl)
        db.session.commit()

    @classmethod
    def update(cls, acl_id, data):
        schema = NewACLEntrySchema()
        updated_acl = schema.load(data)
        if not updated_acl:
            return
        acl = cls.query.get(acl_id)
        acl.name = updated_acl.name
        acl.description = updated_acl.description
        acl.item_type = updated_acl.item_type
        acl.item_id = updated_acl.item_id
        acl.everyone = updated_acl.everyone
        acl.see = updated_acl.see
        acl.access = updated_acl.access
        acl.modify = updated_acl.modify
        acl.users = updated_acl.users
        acl.roles = updated_acl.roles
        db.session.commit()

    @classmethod
    def delete(cls, id):
        acl = cls.query.get(id)
        db.session.delete(acl)
        db.session.commit()

    @classmethod
    def apply_query(cls, query: BaseQuery, user: User, see: bool, access: bool, modify: bool) -> BaseQuery:
        roles = [role.id for role in user.roles]

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
                        ACLEntry.see is True,
                        or_(
                            ACLEntry.everyone is True,
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
                        ACLEntry.access is True,
                        or_(
                            ACLEntry.everyone is True,
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
                        ACLEntry.modify is True,
                        or_(
                            ACLEntry.everyone is True,
                            ACLEntryUser.user_id == user.id,
                            ACLEntryRole.role_id.in_(roles),
                        ),
                    ),
                )
            )

        return query.filter(
            or_(
                ACLEntry.id is not None,
                ACLEntry.everyone is True,
                ACLEntryUser.user_id == user.id,
                ACLEntryRole.role_id.in_(roles),
            )
        )


class ACLEntryUser(db.Model):
    acl_entry_id = db.Column(db.Integer, db.ForeignKey("acl_entry.id"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)


class ACLEntryRole(db.Model):
    acl_entry_id = db.Column(db.Integer, db.ForeignKey("acl_entry.id"), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), primary_key=True)

from marshmallow import fields, post_load
from sqlalchemy import func, or_, orm
from werkzeug.security import generate_password_hash

from core.managers.db_manager import db
from core.model.role import Role
from core.model.permission import Permission
from core.model.organization import Organization
from shared.schema.user import (
    UserSchemaBase,
    UserProfileSchema,
    HotkeySchema,
    UserPresentationSchema,
)
from shared.schema.role import RoleIdSchema, PermissionIdSchema
from shared.schema.organization import OrganizationIdSchema
from core.managers.log_manager import logger


class NewUserSchema(UserSchemaBase):
    roles = fields.Nested(RoleIdSchema, many=True)
    permissions = fields.Nested(PermissionIdSchema, many=True)
    organizations = fields.Nested(OrganizationIdSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        return User(**data)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(), nullable=False)
    password = db.Column(db.String(), nullable=True)

    organizations = db.relationship("Organization", secondary="user_organization")

    roles = db.relationship(Role, secondary="user_role")
    permissions = db.relationship(Permission, secondary="user_permission")

    profile_id = db.Column(db.Integer, db.ForeignKey("user_profile.id"))
    profile = db.relationship("UserProfile", cascade="all")

    def __init__(self, id, username, name, password, organizations, roles, permissions):
        self.id = None
        self.username = username
        self.name = name
        self.password = password
        self.organizations = [Organization.find(organization.id) for organization in organizations]
        self.roles = [Role.find(role.id) for role in roles]
        self.permissions = [Permission.find(permission.id) for permission in permissions]
        self.profile = UserProfile(True, False, [])
        self.tag = "mdi-account"

    @orm.reconstructor
    def reconstruct(self):
        self.tag = "mdi-account"

    @classmethod
    def find(cls, username):
        return cls.query.filter_by(username=username).first()

    @classmethod
    def find_by_id(cls, user_id):
        return cls.query.get(user_id)

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(User.name)).all()

    @classmethod
    def get(cls, search, organization):
        query = cls.query

        if organization is not None:
            query = query.join(UserOrganization, User.id == UserOrganization.user_id)

        if search is not None:
            search_string = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(User.name).like(search_string),
                    func.lower(User.username).like(search_string),
                )
            )

        return query.order_by(db.asc(User.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        users, count = cls.get(search, None)
        user_schema = UserPresentationSchema(many=True)
        return {"total_count": count, "items": user_schema.dump(users)}

    @classmethod
    def get_all_external_json(cls, user, search):
        users, count = cls.get(search, user.organizations[0])
        user_schema = UserPresentationSchema(many=True)
        return {"total_count": count, "items": user_schema.dump(users)}

    @classmethod
    def add_new(cls, data):
        new_user_schema = NewUserSchema()
        user = new_user_schema.load(data)
        db.session.add(user)
        db.session.commit()

    @classmethod
    def add_new_external(cls, user, permissions, data):
        new_user_schema = NewUserSchema()
        new_user = new_user_schema.load(data)
        new_user.roles = []
        new_user.organizations = user.organizations

        for permission in new_user.permissions[:]:
            if permission.id not in permissions:
                new_user.permissions.remove(permission)

        db.session.add(new_user)
        db.session.commit()

    @classmethod
    def update(cls, user_id, data):
        schema = NewUserSchema()
        updated_user = schema.load(data)
        user = cls.query.get(user_id)
        user.password = generate_password_hash(updated_user.password, method="sha256")
        user.username = updated_user.username
        user.name = updated_user.name
        user.organizations = updated_user.organizations
        user.roles = updated_user.roles
        user.permissions = updated_user.permissions
        db.session.commit()

    @classmethod
    def update_external(cls, user, permissions, user_id, data):
        schema = NewUserSchema()
        updated_user = schema.load(data)
        existing_user = cls.query.get(user_id)

        if any(org in user.organizations for org in existing_user.organizations):
            existing_user.username = updated_user.username
            existing_user.name = updated_user.name

            for permission in updated_user.permissions[:]:
                if permission.id not in permissions:
                    updated_user.permissions.remove(permission)

            existing_user.permissions = updated_user.permissions

            db.session.commit()

    @classmethod
    def delete(cls, id):
        user = cls.query.get(id)
        db.session.delete(user)
        db.session.commit()

    @classmethod
    def delete_external(cls, user, id):
        existing_user = cls.query.get(id)
        if any(org in user.organizations for org in existing_user.organizations):
            db.session.delete(existing_user)
            db.session.commit()

    def get_permissions(self):
        all_permissions = {permission.id for permission in self.permissions}

        for role in self.roles:
            all_permissions.update(role.get_permissions())
        return list(all_permissions)

    def get_current_organization_name(self):
        return self.organizations[0].name if len(self.organizations) > 0 else ""

    @classmethod
    def get_profile_json(cls, user):
        profile_schema = UserProfileSchema()
        return profile_schema.dump(user.profile)

    @classmethod
    def update_profile(cls, user, data):
        new_profile_schema = NewUserProfileSchema()
        updated_profile = new_profile_schema.load(data)

        user.profile.spellcheck = updated_profile.spellcheck
        user.profile.dark_theme = updated_profile.dark_theme

        user.profile.hotkeys = updated_profile.hotkeys

        db.session.commit()

        return cls.get_profile_json(user)


class UserOrganization(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organization.id"), primary_key=True)


class UserRole(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), primary_key=True)


class UserPermission(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    permission_id = db.Column(db.String, db.ForeignKey("permission.id"), primary_key=True)


class NewHotkeySchema(HotkeySchema):
    @post_load
    def make(self, data, **kwargs):
        return Hotkey(**data)


class NewUserProfileSchema(UserProfileSchema):
    hotkeys = fields.List(fields.Nested(NewHotkeySchema))

    @post_load
    def make(self, data, **kwargs):
        return UserProfile(**data)


class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    spellcheck = db.Column(db.Boolean, default=True)
    dark_theme = db.Column(db.Boolean, default=False)

    hotkeys = db.relationship("Hotkey", cascade="all, delete-orphan")

    def __init__(self, spellcheck, dark_theme, hotkeys):
        self.id = None
        self.spellcheck = spellcheck
        self.dark_theme = dark_theme
        self.hotkeys = hotkeys


class UserProfileWordList(db.Model):
    user_profile_id = db.Column(db.Integer, db.ForeignKey("user_profile.id"), primary_key=True)


class Hotkey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key_code = db.Column(db.Integer)
    key = db.Column(db.String)
    alias = db.Column(db.String)

    user_profile_id = db.Column(db.Integer, db.ForeignKey("user_profile.id"))

    def __init__(self, key_code, key, alias):
        self.id = None
        self.key_code = key_code
        self.key = key
        self.alias = alias

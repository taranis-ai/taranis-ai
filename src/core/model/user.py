from managers.db_manager import db
from model.role import Role
from model.permission import Permission
from model.organization import Organization
from marshmallow import fields, post_load
from taranisng.schema.user import UserSchemaBase, UserSchema, UserProfileSchema, HotkeySchema, UserPresentationSchema
from taranisng.schema.role import RoleIdSchema, PermissionIdSchema
from taranisng.schema.organization import OrganizationIdSchema
from taranisng.schema.word_list import WordListIdSchema
from sqlalchemy import func, or_, orm


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

    organizations = db.relationship("Organization", secondary="user_organization")

    roles = db.relationship(Role, secondary='user_role')
    permissions = db.relationship(Permission, secondary='user_permission')

    profile_id = db.Column(db.Integer, db.ForeignKey('user_profile.id'))
    profile = db.relationship("UserProfile", cascade="all")

    def __init__(self, id, username, name, organizations, roles, permissions):
        self.id = None
        self.username = username
        self.name = name
        self.organizations = []
        for organization in organizations:
            self.organizations.append(Organization.find(organization.id))

        self.roles = []
        for role in roles:
            self.roles.append(Role.find(role.id))

        self.permissions = []
        for permission in permissions:
            self.permissions.append(Permission.find(permission.id))

        self.profile = UserProfile(True, False, [], [])
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        self.title = self.name
        self.subtitle = self.username
        self.tag = "mdi-account"

    @classmethod
    def find(cls, username):
        user = cls.query.filter_by(username=username).first()
        return user

    @classmethod
    def find_by_id(cls, user_id):
        user = cls.query.get(user_id)
        return user

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(User.name)).all()

    @classmethod
    def get(cls, search, organization):
        query = cls.query

        if organization is not None:
            query = query.join(UserOrganization, User.id == UserOrganization.user_id)

        if search is not None:
            search_string = '%' + search.lower() + '%'
            query = query.filter(or_(
                func.lower(User.name).like(search_string),
                func.lower(User.username).like(search_string)))

        return query.order_by(db.asc(User.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        users, count = cls.get(search, None)
        user_schema = UserPresentationSchema(many=True)
        return {'total_count': count, 'items': user_schema.dump(users)}

    @classmethod
    def get_all_external_json(cls, user, search):
        users, count = cls.get(search, user.organizations[0])
        user_schema = UserPresentationSchema(many=True)
        return {'total_count': count, 'items': user_schema.dump(users)}

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
        all_permissions = set()

        for permission in self.permissions:
            all_permissions.add(permission.id)

        for role in self.roles:
            all_permissions.update(role.get_permissions())

        return list(all_permissions)

    def get_current_organization_name(self):
        if len(self.organizations) > 0:
            return self.organizations[0].name
        else:
            return ""

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

        user.profile.word_lists = []
        from model.word_list import WordList
        for word_list in updated_profile.word_lists:
            if WordList.allowed_with_acl(word_list.id, user, True, False, False):
                user.profile.word_lists.append(word_list)

        user.profile.hotkeys = updated_profile.hotkeys

        db.session.commit()

        return cls.get_profile_json(user)


class UserOrganization(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), primary_key=True)


class UserRole(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), primary_key=True)


class UserPermission(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    permission_id = db.Column(db.String, db.ForeignKey('permission.id'), primary_key=True)


class NewHotkeySchema(HotkeySchema):

    @post_load
    def make(self, data, **kwargs):
        return Hotkey(**data)


class NewUserProfileSchema(UserProfileSchema):
    word_lists = fields.List(fields.Nested(WordListIdSchema))
    hotkeys = fields.List(fields.Nested(NewHotkeySchema))

    @post_load
    def make(self, data, **kwargs):
        return UserProfile(**data)


class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    spellcheck = db.Column(db.Boolean, default=True)
    dark_theme = db.Column(db.Boolean, default=False)

    hotkeys = db.relationship("Hotkey", cascade="all, delete-orphan")
    word_lists = db.relationship('WordList', secondary='user_profile_word_list')

    def __init__(self, spellcheck, dark_theme, hotkeys, word_lists):
        self.id = None
        self.spellcheck = spellcheck
        self.dark_theme = dark_theme
        self.hotkeys = hotkeys

        self.word_lists = []
        from model.word_list import WordList
        for word_list in word_lists:
            self.word_lists.append(WordList.find(word_list.id))


class UserProfileWordList(db.Model):
    user_profile_id = db.Column(db.Integer, db.ForeignKey('user_profile.id'), primary_key=True)
    word_list_id = db.Column(db.Integer, db.ForeignKey('word_list.id'), primary_key=True)


class Hotkey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key_code = db.Column(db.Integer)
    key = db.Column(db.String)
    alias = db.Column(db.String)

    user_profile_id = db.Column(db.Integer, db.ForeignKey('user_profile.id'))

    def __init__(self, key_code, key, alias):
        self.id = None
        self.key_code = key_code
        self.key = key
        self.alias = alias

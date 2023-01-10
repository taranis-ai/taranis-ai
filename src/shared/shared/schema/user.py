from marshmallow import Schema, fields, post_load, EXCLUDE

from shared.schema.role import RoleSchema, PermissionSchema
from shared.schema.organization import OrganizationSchema
from shared.schema.word_list import WordListSchema
from shared.schema.presentation import PresentationSchema


class UserSchemaBase(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()
    username = fields.Str()
    name = fields.Str()
    password = fields.Str()


class UserSchema(UserSchemaBase):
    roles = fields.Nested(RoleSchema, many=True)
    permissions = fields.Nested(PermissionSchema, many=True)
    organizations = fields.Nested(OrganizationSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        return User(**data)


class UserPresentationSchema(UserSchema, PresentationSchema):
    class Meta:
        unknown = EXCLUDE
        exclude = ["password"]


class User:
    def __init__(self, username, name, permissions):
        self.username = username
        self.name = name
        self.permissions = permissions


class UserIdSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()

    @post_load
    def make(self, data, **kwargs):
        return UserId(**data)


class UserId:
    def __init__(self, id):
        self.id = id


class HotkeySchema(Schema):
    class Meta:
        unknown = EXCLUDE

    key_code = fields.Int(load_default=None)
    key = fields.Str(load_default=None)
    alias = fields.Str()


class UserProfileSchema(Schema):
    spellcheck = fields.Bool()
    dark_theme = fields.Bool()
    word_lists = fields.List(fields.Nested(WordListSchema))
    hotkeys = fields.Nested(HotkeySchema, many=True)

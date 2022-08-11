from marshmallow import Schema, fields, post_load, EXCLUDE

from shared.schema.presentation import PresentationSchema


class PermissionSchema(Schema):
    id = fields.Str()
    name = fields.Str()
    description = fields.Str()


class PermissionIdSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str()

    @post_load
    def make(self, data, **kwargs):
        return PermissionId(**data)


class PermissionId:
    def __init__(self, id):
        self.id = id


class RoleSchemaBase(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str()
    name = fields.Str()
    description = fields.Str()


class RoleSchema(RoleSchemaBase):
    permissions = fields.Nested(PermissionSchema, many=True)


class RolePresentationSchema(RoleSchema, PresentationSchema):
    pass


class RoleIdSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str()

    @post_load
    def make(self, data, **kwargs):
        return RoleId(**data)


class RoleId:
    def __init__(self, id):
        self.id = id

from managers.db_manager import db
from model.permission import Permission
from marshmallow import fields, post_load
from taranisng.schema.role import RoleSchemaBase, RoleSchema, PermissionIdSchema, RolePresentationSchema
from sqlalchemy import func, or_, orm


class NewRoleSchema(RoleSchemaBase):
    permissions = fields.Nested(PermissionIdSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        return Role(**data)


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String())

    permissions = db.relationship(Permission, secondary='role_permission')

    def __init__(self, id, name, description, permissions):
        self.id = None
        self.name = name
        self.description = description
        self.permissions = []
        for permission in permissions:
            self.permissions.append(Permission.find(permission.id))

        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-account-arrow-right"

    @classmethod
    def find(cls, role_id):
        role = cls.query.get(role_id)
        return role

    @classmethod
    def find_by_name(cls, role_name):
        role = cls.query.filter_by(name=role_name).first()
        return role

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(Role.name)).all()

    @classmethod
    def get(cls, search):
        query = cls.query

        if search is not None:
            search_string = '%' + search.lower() + '%'
            query = query.filter(or_(
                func.lower(Role.name).like(search_string),
                func.lower(Role.description).like(search_string)))

        return query.order_by(db.asc(Role.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        roles, count = cls.get(search)
        roles_schema = RolePresentationSchema(many=True)
        return {'total_count': count, 'items': roles_schema.dump(roles)}

    @classmethod
    def add_new(cls, data):
        new_role_schema = NewRoleSchema()
        role = new_role_schema.load(data)
        db.session.add(role)
        db.session.commit()

    def get_permissions(self):
        all_permissions = set()
        for permission in self.permissions:
            all_permissions.add(permission.id)

        return all_permissions

    @classmethod
    def update(cls, role_id, data):
        schema = NewRoleSchema()
        updated_role = schema.load(data)
        role = cls.query.get(role_id)
        role.name = updated_role.name
        role.description = updated_role.description
        role.permissions = updated_role.permissions
        db.session.commit()

    @classmethod
    def delete(cls, id):
        role = cls.query.get(id)
        db.session.delete(role)
        db.session.commit()


class RolePermission(db.Model):
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), primary_key=True)
    permission_id = db.Column(db.String, db.ForeignKey('permission.id'), primary_key=True)

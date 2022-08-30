from sqlalchemy import func, or_

from core.managers.db_manager import db
from shared.schema.role import PermissionSchema


class Permission(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String(), unique=True, nullable=False)
    description = db.Column(db.String())

    roles = db.relationship("Role", secondary="role_permission")

    @classmethod
    def find(cls, permission_id):
        permission = cls.query.get(permission_id)
        return permission

    @classmethod
    def add(cls, id, name, description):
        permission = cls.find(id)
        if permission is None:
            permission = Permission()
            permission.id = id
            permission.name = name
            permission.description = description
            db.session.add(permission)
        else:
            permission.name = name
            permission.description = description
        db.session.commit()

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(Permission.id)).all()

    @classmethod
    def get(cls, search):
        query = cls.query

        if search is not None:
            search_string = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Permission.name).like(search_string),
                    func.lower(Permission.description).like(search_string),
                )
            )

        return query.order_by(db.asc(Permission.id)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        permissions, count = cls.get(search)
        permissions_schema = PermissionSchema(many=True)
        return {"total_count": count, "items": permissions_schema.dump(permissions)}

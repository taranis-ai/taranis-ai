from sqlalchemy import or_

from core.managers.db_manager import db
from core.model.base_model import BaseModel


class Permission(BaseModel):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String(), unique=True, nullable=False)
    description = db.Column(db.String())

    roles = db.relationship("Role", secondary="role_permission")

    def __init__(self, name, description, id=None):
        self.id = id
        self.name = name
        self.description = description

    @classmethod
    def add(cls, id, name, description) -> str:
        if permission := cls.get(id):
            return f"{permission.name} already exists."
        permission = cls(id=id, name=name, description=description)
        db.session.add(permission)
        db.session.commit()
        return f"Successfully created {permission.id}"

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(Permission.id)).all()

    @classmethod
    def get_all_ids(cls):
        return [permission.id for permission in cls.get_all()]

    @classmethod
    def get_by_filter(cls, search):
        query = cls.query

        if search is not None:
            query = query.filter(
                or_(
                    Permission.name.ilike(f"%{search}%"),
                    Permission.description.ilike(f"%{search}%"),
                )
            )

        return query.order_by(db.asc(Permission.id)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        permissions, count = cls.get_by_filter(search)
        items = [permission.to_dict() for permission in permissions]
        return {"total_count": count, "items": items}

    @staticmethod
    def get_external_permissions_ids():
        return ["MY_ASSETS_ACCESS", "MY_ASSETS_CREATE", "MY_ASSETS_CONFIG"]

    @classmethod
    def get_external_permissions(cls):
        return [cls.get(permission_id) for permission_id in cls.get_external_permissions_ids()]

    @classmethod
    def get_external_permissions_json(cls):
        permissions = cls.get_external_permissions()
        items = [permission.to_dict() if permission else None for permission in permissions]
        return {"total_count": len(items), "items": items}

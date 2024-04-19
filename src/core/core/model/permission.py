from sqlalchemy import or_
from sqlalchemy.sql.expression import Select
from typing import Any

from core.managers.db_manager import db
from core.model.base_model import BaseModel


class Permission(BaseModel):
    id = db.Column(db.String, primary_key=True)
    name: Any = db.Column(db.String(), unique=True, nullable=False)
    description: Any = db.Column(db.String())

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
    def get_all_ids(cls):
        permissions = cls.get_all()
        return [permission.id for permission in permissions] if permissions else []

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

        return query.order_by(db.asc(cls.name))

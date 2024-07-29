from typing import TYPE_CHECKING
from sqlalchemy.sql.expression import Select
from sqlalchemy.orm import Mapped, relationship

from core.managers.db_manager import db
from core.model.base_model import BaseModel

if TYPE_CHECKING:
    from core.model.role import Role


class Permission(BaseModel):
    __tablename__ = "permission"

    id: Mapped[str] = db.Column(db.String, primary_key=True)
    name: Mapped[str] = db.Column(db.String(), unique=True, nullable=False)
    description: Mapped[str] = db.Column(db.String())

    roles: Mapped[list["Role"]] = relationship("Role", secondary="role_permission")

    def __init__(self, name, description, id=None):
        if id:
            self.id = id
        self.name = name
        self.description = description

    @classmethod
    def add(cls, id: str, name: str, description: str) -> str:
        if permission := cls.get(id):
            return f"{permission.name} already exists."
        permission = cls(id=id, name=name, description=description)
        db.session.add(permission)
        db.session.commit()
        return f"Successfully created {permission.id}"

    @classmethod
    def get_all_ids(cls):
        permissions = cls.get_all_for_collector()
        return [permission.id for permission in permissions] if permissions else []

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        query = db.select(cls)

        if search := filter_args.get("search"):
            query = query.where(
                db.or_(
                    cls.name.ilike(f"%{search}%"),
                    cls.description.ilike(f"%{search}%"),
                )
            )

        return query.order_by(db.asc(cls.name))

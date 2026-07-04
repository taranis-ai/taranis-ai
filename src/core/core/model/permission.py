from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql.expression import Select

from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel


if TYPE_CHECKING:
    from core.model.role import Role


class Permission(BaseModel):
    __tablename__ = "permission"

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    code: Mapped[str] = db.Column(db.String(), unique=True, nullable=False)
    name: Mapped[str] = db.Column(db.String(), unique=True, nullable=False)
    description: Mapped[str] = db.Column(db.String())

    roles: Mapped[list["Role"]] = relationship("Role", secondary="role_permission")

    def __init__(self, name, description, id=None, code=None):
        self.id = self.uuid7_str()
        if id:
            try:
                self.id = self.normalize_uuid_id(id)
            except ValueError:
                code = code or str(id)
        self.code = code or str(id)
        self.name = name
        self.description = description

    @classmethod
    def add(cls, id: str, name: str, description: str) -> str:
        if permission := cls.get_by_code(id):
            return f"{permission.name} already exists."
        permission = cls(id=id, name=name, description=description)
        db.session.add(permission)
        db.session.commit()
        return f"Successfully created {permission.code}"

    @classmethod
    def get(cls, item_id: str) -> "Permission | None":
        if item_id is None:
            return None
        lookup_id = str(item_id)
        if permission := super().get(lookup_id):
            return permission
        try:
            normalized_id = cls.normalize_uuid_id(item_id)
        except (TypeError, ValueError):
            normalized_id = None
        if normalized_id and normalized_id != lookup_id:
            if permission := super().get(normalized_id):
                return permission
        if lookup_id:
            return cls.get_by_code(lookup_id)
        return None

    @classmethod
    def get_by_code(cls, code: str) -> "Permission | None":
        return cls.get_first(db.select(cls).filter_by(code=code))

    @classmethod
    def get_all_ids(cls):
        permissions = cls.get_all_for_collector()
        return [permission.code for permission in permissions] if permissions else []

    @classmethod
    def get_bulk(cls, item_ids: list[str]) -> list["Permission"]:
        if not item_ids:
            return []
        return list(db.session.execute(db.select(cls).filter(cls.code.in_(item_ids))).scalars().all())

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

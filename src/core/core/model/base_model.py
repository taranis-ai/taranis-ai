import base64
import json
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Sequence, Type, TypeVar

from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.sql import Select

from core.log import logger
from core.managers.db_manager import db


T = TypeVar("T", bound="BaseModel")


class BaseModel(db.Model):
    __allow_unmapped__ = True
    __abstract__ = True

    if TYPE_CHECKING:
        id: Mapped[int | str]

    def __str__(self) -> str:
        return f"{self.__class__.__name__}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"

    def update(self, item: dict[str, Any]) -> tuple[dict, int]:
        for key, value in item.items():
            if hasattr(self, key) and key != "id":
                setattr(self, key, value)

        db.session.commit()
        return {"message": f"{self.__class__.__name__} successfully updated"}, 200

    def to_dict(self) -> dict[str, Any]:
        table = getattr(self, "__table__", None)
        if table is None:
            return {}
        data = {c.name: getattr(self, c.name) for c in table.columns}
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.astimezone().isoformat()
            elif isinstance(value, Enum):
                data[key] = value.value
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def delete(cls: Type[T], id) -> tuple[dict[str, Any], int]:
        if item := cls.get(id):
            db.session.delete(item)
            db.session.commit()
            return {"message": f"{cls.__name__} {id} deleted"}, 200
        logger.warning(f"{cls.__name__} {id} not found")
        return {"error": f"{cls.__name__} {id} not found"}, 404

    @classmethod
    def add(cls: Type[T], data) -> T:
        item = cls.from_dict(data)
        db.session.add(item)
        db.session.commit()
        return item

    @classmethod
    def add_multiple(cls: Type[T], json_data) -> list[T]:
        items = cls.load_multiple(json_data)
        db.session.add_all(items)
        db.session.commit()
        return items

    @classmethod
    def delete_all(cls: Type[T]) -> tuple[dict[str, Any], int]:
        db.session.execute(db.delete(cls))
        db.session.commit()
        logger.debug(f"All {cls.__name__} deleted")
        return {"message": f"All {cls.__name__} deleted"}, 200

    @classmethod
    def from_dict(cls: Type[T], data: dict[str, Any]) -> T:
        return cls(**data)

    @classmethod
    def load_multiple(cls: Type[T], json_data: list[dict[str, Any]]) -> list[T]:
        return [cls.from_dict(data) for data in json_data]

    @classmethod
    def to_list(cls, objects: list[T] | Sequence[T]) -> list[dict[str, Any]]:
        return [obj.to_dict() for obj in objects]

    @classmethod
    def get(cls: Type[T], item_id: str | int) -> T | None:
        if (isinstance(item_id, int) and (item_id < 0 or item_id > 2**63 - 1)) or item_id is None:
            return None
        return db.session.get(cls, item_id)

    @classmethod
    def get_all_for_collector(cls: Type[T]) -> Sequence[T] | None:
        return db.session.execute(db.select(cls)).scalars().all()

    @classmethod
    def get_bulk(cls: Type[T], item_ids: list[int] | list[str]) -> list[T]:
        return list(db.session.execute(db.select(cls).filter(cls.id.in_(item_ids))).scalars().all())

    @classmethod
    def get_for_api(cls, item_id) -> tuple[dict[str, Any], int]:
        if item := cls.get(item_id):
            return item.to_dict(), 200
        return {"error": f"{cls.__name__} {item_id} not found"}, 404

    @classmethod
    def get_filter_query_with_acl(cls, filter_args: dict, user) -> Select:
        return cls.get_filter_query(filter_args)

    @classmethod
    def get_filter_query(cls: Type[T], filter_args: dict) -> Select:
        query = db.select(cls)

        if search := filter_args.get("search"):
            query = query.filter(cls.id.ilike(f"%{search}%"))

        return query

    @classmethod
    def get_filtered(cls: Type[T], query: Select) -> Sequence[T] | None:
        return db.session.execute(query).scalars().all()

    @classmethod
    def get_first(cls: Type[T], query: Select) -> T | None:
        return db.session.execute(query).scalar()

    @classmethod
    def get_by_filter(cls: Type[T], filter_args: dict) -> Sequence[T] | None:
        return cls.get_filtered(cls.get_filter_query(filter_args))

    @classmethod
    def get_all_for_api(cls, filter_args: dict | None, with_count: bool = False, user=None) -> tuple[dict[str, Any], int]:
        filter_args = filter_args or {}
        logger.debug(f"Filtering {cls.__name__} with {filter_args}")
        if user:
            query = cls.get_filter_query_with_acl(filter_args, user)
        else:
            query = cls.get_filter_query(filter_args)
        items = cls.get_filtered(query) or []
        if with_count:
            count = cls.get_filtered_count(query)
            return {"total_count": count, "items": cls.to_list(items)}, 200
        return {"items": cls.to_list(items)}, 200

    @classmethod
    def get_filtered_count(cls: Type[T], query: Select) -> int:
        count_query = db.select(func.count()).select_from(query).order_by(None).offset(None).limit(None)
        return db.session.execute(count_query).scalar() or 0

    @classmethod
    def get_count(cls: Type[T]) -> int:
        count_query = db.select(func.count()).select_from(cls)
        return db.session.execute(count_query).scalar() or 0

    def is_valid_base64(self, s) -> bytes | None:
        try:
            return base64.b64decode(s, validate=True)
        except Exception:
            return None

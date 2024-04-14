from typing import Any, TypeVar, Type
from datetime import datetime
from enum import Enum
import json
from sqlalchemy.sql import Select
from sqlalchemy import func

from core.managers.db_manager import db

T = TypeVar("T", bound="BaseModel")


class BaseModel(db.Model):
    __allow_unmapped__ = True
    __abstract__ = True

    def __str__(self) -> str:
        return f"{self.__class__.__name__} {self.to_json()}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} {self.to_json()}"

    @classmethod
    def delete(cls: Type[T], id) -> tuple[dict[str, Any], int]:
        if item := cls.get(id):
            db.session.delete(item)
            db.session.commit()
            return {"message": f"{cls.__name__} {id} deleted"}, 200
        return {"error": f"{cls.__name__} {id} not found"}, 404

    @classmethod
    def add(cls: Type[T], data) -> T:
        item = cls.from_dict(data)
        db.session.add(item)
        db.session.commit()
        return item

    @classmethod
    def add_multiple(cls: Type[T], json_data) -> list[T]:
        result = []
        for data in json_data:
            item = cls.from_dict(data)
            db.session.add(item)
            result.append(item)

        db.session.commit()
        return result

    @classmethod
    def from_dict(cls: Type[T], data: dict[str, Any]) -> T:
        return cls(**data)

    @classmethod
    def load_multiple(cls: Type[T], json_data: list[dict[str, Any]]) -> list[T]:
        return [cls.from_dict(data) for data in json_data]

    def update(self, item: dict[str, Any]) -> tuple[dict, int]:
        for key, value in item.items():
            if hasattr(self, key) and key != "id":
                setattr(self, key, value)

        db.session.commit()
        return {"message": f"Successfully updated {self.id}"}, 200

    def to_dict(self) -> dict[str, Any]:
        table = getattr(self, "__table__", None)
        if table is None:
            return {}
        data = {c.name: getattr(self, c.name) for c in table.columns}
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, Enum):
                data[key] = value.value
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def to_list(cls, objects: list[T]) -> list[dict[str, Any]]:
        return [obj.to_dict() for obj in objects]

    @classmethod
    def get(cls: Type[T], item_id) -> T | None:
        if (isinstance(item_id, int) and (item_id < 0 or item_id > 2**63 - 1)) or item_id is None:
            return None
        return db.session.get(cls, item_id)

    @classmethod
    def get_all(cls: Type[T]) -> list[T] | None:
        return db.session.execute(db.select(cls)).scalars().all()

    @classmethod
    def get_for_api(cls, item_id) -> tuple[dict[str, Any], int]:
        if item := cls.get(item_id):
            return item.to_dict(), 200
        return {"error": f"{cls.__name__} {item_id} not found"}, 404

    @classmethod
    def get_filter_query(cls: Type[T], search=None) -> Select:
        query = db.select(cls)

        if search:
            query = query.where(db.or_(*[column.ilike(f"%{search}%") for column in cls.__table__.columns]))

        return query

    @classmethod
    def get_filtered(cls: Type[T], query: Select) -> list[T] | None:
        return db.session.execute(query).scalars().all()

    @classmethod
    def get_by_filter(cls: Type[T], search=None) -> list[T] | None:
        return cls.get_filtered(cls.get_filter_query(search))

    @classmethod
    def get_all_for_api(cls: Type[T], search=None, with_count: bool = False) -> tuple[dict[str, Any], int]:
        query = cls.get_filter_query(search)
        items = cls.get_filtered(query)
        if not items:
            return {"items": []}, 404
        if with_count:
            count = cls.get_filtered_count(query)
            return {"count": count, "items": cls.to_list(items)}, 200
        return {"items": cls.to_list(items)}, 200

    @classmethod
    def get_filtered_count(cls: Type[T], query: Select) -> int:
        count_query = db.select(func.count()).select_from(query).order_by(None)
        return db.session.execute(count_query).scalar() or 0

import json
import csv
from typing import Any
from enum import IntEnum
from sqlalchemy.sql import Select
from sqlalchemy.orm import Mapped, relationship

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.user import User
from core.model.role_based_access import RoleBasedAccess, ItemType
from core.log import logger
from core.service.role_based_access import RBACQuery, RoleBasedAccessService


class WordListUsage(IntEnum):
    COLLECTOR_INCLUDELIST = 1  # 2^0
    COLLECTOR_EXCLUDELIST = 2  # 2^1
    TAGGING_BOT = 4  # 2^2


class WordList(BaseModel):
    __tablename__ = "word_list"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    name: Mapped[str] = db.Column(db.String(), nullable=False)
    description: Mapped[str] = db.Column(db.String(), default=None)
    usage: Mapped[int] = db.Column(db.Integer, default=0)
    link: Mapped[str] = db.Column(db.String(), nullable=True, default=None)
    entries: Mapped[list["WordListEntry"]] = relationship("WordListEntry", cascade="all, delete")

    def __init__(self, name: str, description: str | None = None, usage: int = 0, link: str = "", entries=None, id: int | None = None):
        if id:
            self.id = id
        self.name = name
        if description:
            self.description = description
        self.update_usage(usage)
        self.link = link
        self.entries = entries or []

    @classmethod
    def find_by_name(cls, name: str) -> "WordList|None":
        return cls.get_first(db.select(cls).filter_by(name=name))

    def add_usage(self, usage_type):
        self.usage |= usage_type

    def remove_usage(self, usage_type):
        self.usage &= ~usage_type

    def has_usage(self, usage_type) -> bool:
        return (self.usage & usage_type) == usage_type

    def get_usage_list(self) -> list[str]:
        return [usage.name for usage in WordListUsage if self.has_usage(usage)]

    def from_usage_list(self, usage_list: list[str]):
        self.usage = 0
        for usage in usage_list:
            if self.is_valid_usage(WordListUsage[usage]):
                self.add_usage(WordListUsage[usage])

    def update_usage(self, usage: list[str] | int):
        if isinstance(usage, list):
            self.from_usage_list(usage)
        elif isinstance(usage, int) and self.is_valid_usage(usage):
            self.usage = usage

    def is_valid_usage(self, usage: int) -> bool:
        if usage == WordListUsage.COLLECTOR_INCLUDELIST and self.usage & WordListUsage.COLLECTOR_EXCLUDELIST:
            return False
        if usage == WordListUsage.COLLECTOR_EXCLUDELIST and self.usage & WordListUsage.COLLECTOR_INCLUDELIST:
            return False
        return usage < (2 ** len(WordListUsage))

    def allowed_with_acl(self, user: User, require_write_access) -> bool:
        if not RoleBasedAccess.is_enabled() or not user:
            return True

        query = RBACQuery(user=user, resource_id=str(self.id), resource_type=ItemType.WORD_LIST, require_write_access=require_write_access)

        return RoleBasedAccessService.user_has_access_to_resource(query)

    @classmethod
    def get_all_empty(cls):
        return cls.get_filtered(db.select(cls).filter_by(entries=None).order_by(db.asc(WordList.name)))

    @classmethod
    def get_filter_query_with_acl(cls, filter_args: dict, user: User) -> Select:
        query = cls.get_filter_query(filter_args)
        rbac = RBACQuery(user=user, resource_type=ItemType.WORD_LIST)
        query = RoleBasedAccessService.filter_query_with_acl(query, rbac)
        return query

    @classmethod
    def get_all_for_api(cls, filter_args: dict | None, with_count: bool = False, user=None) -> tuple[dict[str, Any], int]:
        filter_args = filter_args or {}
        logger.debug(f"Filtering {cls.__name__} with {filter_args}")
        if user:
            query = cls.get_filter_query_with_acl(filter_args, user)
        else:
            query = cls.get_filter_query(filter_args)
        items = cls.get_filtered(query) or []
        if filter_args.get("with_entries"):
            result_items = [item.to_dict() for item in items]
        else:
            result_items = [item.to_small_dict() for item in items]
        if with_count:
            count = cls.get_filtered_count(query)
            return {"total_count": count, "items": result_items}, 200
        return {"items": result_items}, 200

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

        if usage := filter_args.get("usage"):
            try:
                query = query.filter(WordList.usage.op("&")(int(usage)) > 0)
            except ValueError:
                logger.error(f"Invalid usage filter: {usage}")

        return query.order_by(db.asc(cls.name))

    def to_small_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["usage"] = self.get_usage_list()
        data.pop("entries", None)
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> "WordList":
        if 'entries' in data:
            data['entries'] = WordListEntry.load_multiple(data['entries'])

        word_list = cls(
            id=data.get('id'), 
            name=data.get('name', ''),
            description=data.get('description'),
            usage=data.get('usage', 0),
            link=data.get('link', ''),
            entries=data.get('entries', [])
        )

        return word_list

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["usage"] = self.get_usage_list()
        data["entries"] = [entry.to_word_list_dict() for entry in self.entries[:1000] if entry]
        data["entry_count"] = len(self.entries)
        return data

    def to_export_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "usage": self.usage,
            "link": self.link,
            "entries": [entry.to_word_list_dict() for entry in self.entries if entry],
        }

    def to_entry_dict(self) -> list[dict[str, Any]]:
        return [entry.to_entry_dict() for entry in self.entries if entry]

    @classmethod
    def update(cls, word_list_id: int, data: dict, user: User | None = None) -> tuple[dict, int]:
        word_list = cls.get(word_list_id)
        if word_list is None:
            return {"error": "WordList not found"}, 404

        if user and not word_list.allowed_with_acl(user, require_write_access=True):
            return {"error": "User does not have write access to WordList"}, 403
        if name := data.get("name"):
            word_list.name = name
        if description := data.get("description"):
            word_list.description = description
        if link := data.get("link"):
            word_list.link = link
        if usage := data.get("usage"):
            word_list.update_usage(usage)

        db.session.commit()
        return {"message": "Word list updated", "id": f"{word_list.id}"}, 200

    @classmethod
    def parse_csv(cls, content) -> list:
        dialect = csv.Sniffer().sniff(content)
        cr = csv.reader(content.splitlines(), dialect)
        headers = [header.lower() for header in next(cr)]
        if len(headers) < 2 or len(headers) > 3:
            raise ValueError("Invalid CSV file")
        return [dict(zip(headers, row)) for row in cr]

    @classmethod
    def parse_json(cls, content) -> list | None:
        file_content = json.loads(content)
        return cls.load_json_content(content=file_content)

    @classmethod
    def load_json_content(cls, content) -> list:
        if content.get("version") != 1:
            raise ValueError("Invalid JSON file")
        if not content.get("data"):
            raise ValueError("No data found")
        return content["data"]

    @classmethod
    def update_word_list(cls, content, content_type, word_list_id: int) -> "WordList | None":
        update_word_list = cls.get(word_list_id)
        if not update_word_list:
            return None

        if content_type == "text/csv":
            data = cls.parse_csv(content)
        elif content_type == "application/json":
            data = cls.load_json_content(content=content)[0]["entries"]
        else:
            return None

        if not data:
            return None

        old_entry_length = len(update_word_list.entries)
        update_word_list.entries.clear()
        update_word_list.entries = WordListEntry.load_multiple(data)
        logger.debug(f"Updated WordList {update_word_list.name} from {old_entry_length} to {len(update_word_list.entries)} entries")
        db.session.commit()

        return update_word_list

    @classmethod
    def export(cls, source_ids=None) -> bytes:
        query = db.select(cls)
        if source_ids:
            query = query.filter(cls.id.in_(source_ids))

        data = cls.get_filtered(query)
        export_data = {"version": 1, "data": [word_list.to_export_dict() for word_list in data]} if data else {}
        return json.dumps(export_data).encode("utf-8")

    @classmethod
    def import_word_lists(cls, file) -> list | None:
        data = cls.parse_word_list_data(file)

        return None if data is None else cls.add_multiple(data)

    @classmethod
    def parse_word_list_data(cls, file) -> list | None:
        file_data = file.read().decode("utf8")
        if file.content_type == "text/csv":
            return [{"entries": cls.parse_csv(file_data), "name": file.filename}]
        elif file.content_type == "application/json":
            return cls.parse_json(file_data)

        return None


class WordListEntry(BaseModel):
    __tablename__ = "word_list_entry"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    value: Mapped[str] = db.Column(db.String(), nullable=False)
    category: Mapped[str] = db.Column(db.String(), nullable=True)
    description: Mapped[str] = db.Column(db.String(), nullable=True)

    word_list_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("word_list.id", ondelete="CASCADE"))

    def __init__(self, value, category="Uncategorized", description="", id=None):
        if id:
            self.id = id
        self.value = value
        self.category = category
        self.description = description

    @classmethod
    def identical(cls, value, word_list_id):
        return db.session.execute(db.exists().where(WordListEntry.value == value).where(WordListEntry.word_list_id == word_list_id)).scalar()

    @classmethod
    def delete_entries(cls, word_list_id, value):
        word_list = WordList.get(word_list_id)
        if not word_list:
            return "WordList not found", 404
        db.session.execute(db.delete(cls).where(cls.word_list_id == word_list_id).where(cls.value == value))
        db.session.commit()

    @classmethod
    def update_word_list_entries(cls, id, entries_data):
        word_list = WordList.get(id)
        if not word_list:
            return "WordList not found", 404

        entries = cls.load_multiple(entries_data)
        if not entries:
            return "No entries found", 404
        for entry in entries:
            if not cls.identical(entry.value, word_list.id):
                word_list.entries.append(entry)
                db.session.commit()
        return "WordList entries updated", 200

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.pop("id")
        return data

    def to_word_list_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.pop("id")
        data.pop("word_list_id")
        return data

    def to_entry_dict(self) -> dict[str, Any]:
        return {"value": self.value, "category": self.category}

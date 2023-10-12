import json
import csv
import sqlalchemy
from typing import Any
from enum import IntEnum
from sqlalchemy import or_, and_
from sqlalchemy.sql.expression import cast

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.acl_entry import ACLEntry, ItemType
from core.managers.log_manager import logger


class WordListUsage(IntEnum):
    COLLECTOR_INCLUDELIST = 1  # 2^0
    COLLECTOR_EXCLUDELIST = 2  # 2^1
    TAGGING_BOT = 4  # 2^2


class WordList(BaseModel):
    id: Any = db.Column(db.Integer, primary_key=True)
    name: Any = db.Column(db.String(), nullable=False)
    description: Any = db.Column(db.String(), default=None)
    usage: Any = db.Column(db.Integer, default=0)
    link: Any = db.Column(db.String(), nullable=True, default=None)
    entries: Any = db.relationship("WordListEntry", cascade="all, delete")

    def __init__(self, name, description=None, usage=0, link=None, entries=None, id=None):
        self.id = id
        self.name = name
        self.description = description
        self.update_usage(usage)
        self.link = link
        self.entries = WordListEntry.load_multiple(entries) if entries else []

    @classmethod
    def find_by_name(cls, name: str) -> "WordList":
        return cls.query.filter_by(name=name).first()

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

    @classmethod
    def allowed_with_acl(cls, word_list_id, user, see, access, modify):
        query = db.session.query(WordList.id).distinct().group_by(WordList.id).filter(WordList.id == word_list_id)

        query = query.outerjoin(
            ACLEntry,
            and_(
                cast(WordList.id, sqlalchemy.String) == ACLEntry.item_id,
                ACLEntry.item_type == ItemType.WORD_LIST,
            ),
        )

        query = ACLEntry.apply_query(query, user, see, access, modify)

        return query.scalar() is not None

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(WordList.name)).all()

    @classmethod
    def get_all_empty(cls):
        return cls.query.filter_by(entries=None).order_by(db.asc(WordList.name)).all()

    @classmethod
    def get_by_filter(cls, filter_data, user=None, acl_check=False):
        query = cls.query.distinct().group_by(WordList.id)

        if acl_check and user:
            query = query.outerjoin(
                ACLEntry,
                and_(
                    cast(WordList.id, sqlalchemy.String) == ACLEntry.item_id,
                    ACLEntry.item_type == ItemType.WORD_LIST,
                ),
            )
            query = ACLEntry.apply_query(query, user, True, False, False)

        if search := filter_data.get("search"):
            search_string = f"%{search}%"
            query = query.filter(
                or_(
                    WordList.name.ilike(search_string),
                    WordList.description.ilike(search_string),
                )
            )

        if usage := filter_data.get("usage"):
            query = query.filter(WordList.usage.op("&")(usage) > 0)

        return query.order_by(db.asc(WordList.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, filter_data, user, acl_check):
        word_lists, count = cls.get_by_filter(filter_data, user, acl_check)
        items = [word_list.to_dict() for word_list in word_lists]
        return {"total_count": count, "items": items}

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["usage"] = self.get_usage_list()
        data["entries"] = [entry.to_word_list_dict() for entry in self.entries if entry]
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
    def update(cls, word_list_id, data) -> tuple[dict, int]:
        word_list = cls.get(word_list_id)
        if word_list is None:
            return {"error": "WordList not found"}, 404

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
    def export(cls, source_ids=None):
        if source_ids:
            data = cls.query.filter(cls.id.in_(source_ids)).all()  # type: ignore
        else:
            data = cls.get_all()
        export_data = {"version": 1, "data": [word_list.to_export_dict() for word_list in data]}
        return json.dumps(export_data).encode("utf-8")

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
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(), nullable=False)
    category = db.Column(db.String(), nullable=True)
    description = db.Column(db.String(), nullable=False)

    word_list_id = db.Column(db.Integer, db.ForeignKey("word_list.id", ondelete="CASCADE"))

    def __init__(self, value, category="Uncategorized", description=""):
        self.id = None
        self.value = value
        self.category = category
        self.description = description

    @classmethod
    def identical(cls, value, word_list_id):
        return db.session.query(db.exists().where(WordListEntry.value == value).where(WordListEntry.word_list_id == word_list_id)).scalar()

    @classmethod
    def delete_entries(cls, id, value):
        word_list = WordList.get(id)
        if not word_list:
            return "WordList not found", 404
        cls.query.filter_by(word_list_id=word_list.id).filter_by(value=value).delete()
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

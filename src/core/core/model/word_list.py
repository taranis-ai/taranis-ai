import json
import sqlalchemy
from typing import Any
from enum import IntEnum
from sqlalchemy import or_, and_
from sqlalchemy.sql.expression import cast

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.acl_entry import ACLEntry, ItemType


class WordListUsage(IntEnum):
    COLLECTOR_WHITELIST = 1  # 2^0
    COLLECTOR_BLACKLIST = 2  # 2^1
    TAGGING_BOT = 4  # 2^2


class WordList(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String(), default=None)
    usage = db.Column(db.Integer, default=0)
    link = db.Column(db.String(), nullable=True, default=None)
    entries = db.relationship("WordListEntry", cascade="all, delete-orphan")

    def __init__(self, name, description=None, usage=0, link=None, entries=None, id=None):
        self.id = id
        self.name = name
        self.description = description
        self.usage = usage
        self.link = link
        self.entries = [WordListEntry.get(entry) for entry in entries] if entries else []

    @classmethod
    def find_by_name(cls, name):
        return cls.query.filter_by(name=name).first()

    def add_usage(self, usage_type):
        self.usage |= usage_type

    def remove_usage(self, usage_type):
        self.usage &= ~usage_type

    def has_usage(self, usage_type):
        return (self.usage & usage_type) == usage_type

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
    def get_by_filter(cls, search, user, acl_check):
        query = cls.query.distinct().group_by(WordList.id)

        if acl_check:
            query = query.outerjoin(
                ACLEntry,
                and_(
                    cast(WordList.id, sqlalchemy.String) == ACLEntry.item_id,
                    ACLEntry.item_type == ItemType.WORD_LIST,
                ),
            )
            query = ACLEntry.apply_query(query, user, True, False, False)

        if search:
            query = query.filter(
                or_(
                    WordList.name.ilike(f"%{search}%"),
                    WordList.description.ilike(f"%{search}%"),  # type: ignore
                )
            )

        return query.order_by(db.asc(WordList.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search, user, acl_check):
        word_lists, count = cls.get_by_filter(search, user, acl_check)
        items = [word_list.to_dict() for word_list in word_lists]
        return {"total_count": count, "items": items}

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["entries"] = [entry.to_word_list_dict() for entry in self.entries if entry]
        data["tag"] = "mdi-format-list-bulleted-square"
        return data

    def to_export_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "use_for_stop_words": self.use_for_stop_words,
            "link": self.link,
            "entries": [entry.to_word_list_dict() for entry in self.entries if entry],
        }

    def to_entry_dict(self) -> list[dict[str, Any]]:
        return [entry.to_entry_dict() for entry in self.entries if entry]

    @classmethod
    def update(cls, word_list_id, data) -> tuple[str, int]:
        word_list = cls.get(word_list_id)
        if word_list is None:
            return "WordList not found", 404
        word_list.entries = [WordListEntry.from_dict(entry) for entry in data.pop("entries")]
        for key, value in data.items():
            if hasattr(word_list, key) and key != "id" and key != "entries":
                setattr(word_list, key, value)
        db.session.commit()
        return "Word list updated", 200

    @classmethod
    def export(cls, source_ids=None):
        if source_ids:
            data = cls.query.filter(cls.id.in_(source_ids)).all()  # type: ignore
        else:
            data = cls.get_all()
        export_data = {"version": 1, "data": [word_list.to_export_dict() for word_list in data]}
        return json.dumps(export_data).encode("utf-8")

    @classmethod
    def import_word_lists(cls, file):
        file_data = file.read()
        json_data = json.loads(file_data.decode("utf8"))
        if json_data["version"] == 1:
            data = json_data["data"]
        else:
            raise ValueError("Unsupported version")
        return cls.add_multiple(data)


class WordListEntry(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(), nullable=False)
    category = db.Column(db.String(), nullable=True)
    description = db.Column(db.String(), nullable=False)

    word_list_id = db.Column(db.Integer, db.ForeignKey("word_list.id"))

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

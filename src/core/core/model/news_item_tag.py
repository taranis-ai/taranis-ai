from sqlalchemy import orm, func
from typing import Any

from core.managers.db_manager import db
from core.model.base_model import BaseModel


class NewsItemTag(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name: Any = db.Column(db.String(255))
    tag_type: Any = db.Column(db.String(255))
    n_i_a_id = db.Column(db.ForeignKey("news_item_aggregate.id"))
    n_i_a = db.relationship("NewsItemAggregate", backref=orm.backref("tags", cascade="all, delete-orphan"))

    def __init__(self, name, tag_type):
        self.id = None
        self.name = name
        self.tag_type = tag_type

    @classmethod
    def delete_all_tags(cls):
        tags = cls.query.all()
        for tag in tags:
            db.session.delete(tag)
        db.session.commit()

    @classmethod
    def get_filtered_tags(cls, filter_args: dict) -> list["NewsItemTag"]:
        query = cls.query.with_entities(cls.name, cls.tag_type)

        if search := filter_args.get("search"):
            query = query.filter(cls.name.ilike(f"%{search}%"))

        if tag_type := filter_args.get("tag_type"):
            query = query.filter(cls.tag_type == tag_type)

        if min_size := filter_args.get("min_size"):
            # returns only tags where the name appears at least min_size times in the database
            query = query.group_by(cls.name, cls.tag_type).having(func.count(cls.name) >= min_size)
            # order by size
            query = query.order_by(func.count(cls.name).desc())

        rows = cls.get_rows(query, filter_args)
        return [cls(name=row[0], tag_type=row[1]) for row in rows]

    @classmethod
    def get_rows(cls, query, filter_args: dict) -> list["NewsItemTag"]:
        offset = filter_args.get("offset", 0)
        limit = filter_args.get("limit", 20)

        return query.offset(offset).limit(limit).all()

    @classmethod
    def get_json(cls, filter_args: dict) -> list[dict[str, Any]]:
        tags = cls.get_filtered_tags(filter_args)
        return [tag.to_small_dict() for tag in tags]

    @classmethod
    def get_list(cls, filter_args: dict) -> list[str]:
        tags = cls.get_filtered_tags(filter_args)
        return [tag.name for tag in tags]

    @classmethod
    def remove_by_aggregate(cls, aggregate):
        tags = cls.query.filter_by(n_i_a_id=aggregate.id).all()
        for tag in tags:
            db.session.delete(tag)
        db.session.commit()

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "tag_type": self.tag_type}

    def to_small_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "tag_type": self.tag_type,
        }

    @classmethod
    def find_by_name(cls, tag_name: str) -> "NewsItemTag | None":
        return cls.query.filter(cls.name.ilike(tag_name)).first()

    @classmethod
    def get_n_biggest_tags_by_type(cls, tag_type: str, n: int, offset: int = 0) -> dict[str, dict]:
        query = (
            cls.query.with_entities(cls.name, func.count(cls.name).label("name_count"))
            .filter(cls.tag_type == tag_type)
            .group_by(cls.name)
            .order_by(db.desc("name_count"))
            .offset(offset)
            .limit(n)
            .all()
        )
        return {row[0]: {"name": row[0], "size": row[1]} for row in query}

    @classmethod
    def apply_sort(cls, query, sort_str: str):
        if not sort_str:
            return query

        parts = sort_str.split("_")
        if len(parts) != 2:
            return query

        column_name, sort_order = parts
        column = getattr(cls, column_name, None)
        if not column:
            return query

        query = query.order_by(column if sort_order == "asc" else db.desc(column))
        return query

    @classmethod
    def get_cluster_by_filter(cls, filter):
        query = cls.query.with_entities(cls.name, func.count(cls.name).label("size"))
        if tag_type := filter.get("tag_type"):
            query = query.filter(cls.tag_type == tag_type).group_by(cls.name)

        count = query.count()

        if search := filter.get("search"):
            query = query.filter(cls.name.ilike(f"%{search}%"))
        if sort := filter.get("sort", "sort_desc"):
            query = cls.apply_sort(query, sort)

        if offset := filter.get("offset"):
            query = query.offset(offset)
        if limit := filter.get("limit"):
            query = query.limit(limit)

        items = {row[0]: {"name": row[0], "size": row[1]} for row in query.all()}

        return {"total_count": count, "items": list(items.values())}

    @classmethod
    def get_tag_types(cls) -> list[tuple[str, int]]:
        query = (
            cls.query.with_entities(cls.tag_type, func.count(cls.name).label("type_count"))
            .group_by(cls.tag_type)
            .order_by(db.desc("type_count"))
            .all()
        )
        return [(row[0], row[1]) for row in query]

    @classmethod
    def parse_tags(cls, tags: list | dict) -> dict[str, "NewsItemTag"]:
        if isinstance(tags, dict):
            return cls._parse_dict_tags(tags)

        return cls._parse_list_tags(tags)

    @classmethod
    def _parse_dict_tags(cls, tags: dict) -> dict[str, "NewsItemTag"]:
        return {tag_name: NewsItemTag(name=tag_name, tag_type=tag.get("tag_type", "misc")) for tag_name, tag in tags.items()}

    @classmethod
    def _parse_list_tags(cls, tags: list) -> dict[str, "NewsItemTag"]:
        new_tags = {}
        for tag in tags:
            if isinstance(tag, dict):
                tag_name = tag.get("name")
                tag_type = tag.get("tag_type", "misc")
            else:
                tag_name = tag
                tag_type = "misc"
            new_tags[tag_name] = NewsItemTag(name=tag_name, tag_type=tag_type)
        return new_tags

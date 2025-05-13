from sqlalchemy import func
from sqlalchemy.orm import Mapped, relationship

from typing import Any, TYPE_CHECKING
from core.managers.db_manager import db
from core.model.base_model import BaseModel

if TYPE_CHECKING:
    from core.model.story import Story


class NewsItemTag(BaseModel):
    __tablename__ = "news_item_tag"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    name: Mapped[str] = db.Column(db.String(255))
    tag_type: Mapped[str] = db.Column(db.String(255))
    story_id: Mapped[str] = db.Column(db.ForeignKey("story.id", ondelete="CASCADE"))
    story: Mapped["Story"] = relationship("Story", back_populates="tags")

    def __init__(self, name, tag_type):
        self.name = name
        self.tag_type = tag_type

    @classmethod
    def get_filtered_tags(cls, filter_args: dict) -> dict[str, str]:
        query = db.select(cls.name, cls.tag_type)

        if search := filter_args.get("search"):
            query = query.filter(cls.name.ilike(f"%{search}%"))

        if tag_type := filter_args.get("tag_type"):
            query = query.filter(cls.tag_type == tag_type)

        if min_size := filter_args.get("min_size"):
            # returns only tags where the name appears at least min_size times in the database
            query = query.group_by(cls.name, cls.tag_type).having(func.count(cls.name) >= min_size)
            query = query.order_by(func.count(cls.name).desc())

        offset = filter_args.get("offset", 0)
        limit = filter_args.get("limit", 20)
        query = query.offset(offset).limit(limit)
        result = db.session.execute(query).tuples()
        return {name: tag_type for name, tag_type in result}

    @classmethod
    def get_list(cls, filter_args: dict) -> list[str]:
        tags = cls.get_filtered_tags(filter_args)
        return list(tags.keys())

    @classmethod
    def remove_by_story(cls, story):
        db.session.execute(db.delete(cls).where(cls.story_id == story.id))
        db.session.commit()

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "tag_type": self.tag_type}

    @classmethod
    def find_by_name(cls, tag_name: str) -> "NewsItemTag | None":
        return cls.get_first(db.select(cls).filter(cls.name.ilike(tag_name)))

    @classmethod
    def apply_sort(cls, query, sort_str: str):
        if sort_str == "size_desc":
            return query.order_by(func.count(cls.name).desc())
        elif sort_str == "size_asc":
            return query.order_by(func.count(cls.name).asc())
        elif sort_str == "name_asc":
            return query.order_by(cls.name.asc())
        elif sort_str == "name_desc":
            return query.order_by(cls.name.desc())

        return query

    @classmethod
    def get_cluster_by_filter(cls, filter_args: dict):
        query = db.select(cls).with_only_columns(cls.name, func.count(cls.name).label("size"))
        if tag_type := filter_args.get("tag_type"):
            query = query.filter(cls.tag_type == tag_type).group_by(cls.name)

        count = cls.get_filtered_count(query)

        if search := filter_args.get("search"):
            query = query.filter(cls.name.ilike(f"%{search}%"))
        if sort := filter_args.get("sort", "size_desc"):
            query = cls.apply_sort(query, sort)

        if offset := filter_args.get("offset"):
            query = query.offset(offset)
        if limit := filter_args.get("limit"):
            query = query.limit(limit)

        results = db.session.execute(query).all()
        items = {row[0]: {"name": row[0], "size": row[1]} for row in results}

        return {"total_count": count, "items": list(items.values())}

    @classmethod
    def parse_tags(cls, tags: list | dict) -> dict[str, "NewsItemTag"]:
        if isinstance(tags, dict):
            return cls._parse_dict_tags(tags)

        return cls._parse_list_tags(tags)

    @classmethod
    def _parse_dict_tags(cls, tags: dict) -> dict[str, "NewsItemTag"]:
        return {tag_name: NewsItemTag(name=tag_name, tag_type=tag_type) for tag_name, tag_type in tags.items()}

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

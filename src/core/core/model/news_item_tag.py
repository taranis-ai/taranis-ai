from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Index, func, literal_column, tuple_
from sqlalchemy.orm import Mapped, relationship

from core.log import logger
from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel


if TYPE_CHECKING:
    from core.model.news_item import NewsItem


class NewsItemTag(BaseModel):
    __tablename__ = "news_item_tag"
    __table_args__ = (
        Index("ix_news_item_tag_news_item_name", "news_item_id", "name"),
        Index("ix_news_item_tag_name_type_item", "name", "tag_type", "news_item_id"),
        Index("ix_news_item_tag_type_name_item", "tag_type", "name", "news_item_id"),
    )

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    name: Mapped[str] = db.Column(db.String(255))
    tag_type: Mapped[str] = db.Column(db.String(255))
    news_item_id: Mapped[str] = db.Column(
        db.String(UUID_STR_LENGTH), db.ForeignKey("news_item.id", ondelete="CASCADE"), nullable=False, index=True
    )
    news_item: Mapped["NewsItem"] = relationship("NewsItem", back_populates="tags")

    def __init__(self, name: str, tag_type: str = "misc"):
        self.id = self.uuid7_str()
        if not isinstance(name, str):
            raise TypeError(f"Tag name must be a string, got {type(name)}")
        self.name = name
        if not isinstance(tag_type, str):
            raise TypeError(f"Tag type must be a string, got {type(tag_type)}")
        self.tag_type = tag_type

    @classmethod
    def get_filtered_tags(cls, filter_args: dict) -> dict[str, str]:
        from core.model.news_item import NewsItem

        story_count = func.count(func.distinct(NewsItem.story_id))
        query = db.select(cls.name, cls.tag_type, story_count.label("story_count")).join(NewsItem)

        if search := filter_args.get("search"):
            query = query.filter(cls.name.ilike(f"%{search}%"))

        if tag_type := filter_args.get("tag_type"):
            query = query.filter(cls.tag_type == tag_type)

        query = query.group_by(cls.name, cls.tag_type)
        if min_size := filter_args.get("min_size"):
            # returns only tags where the name appears at least min_size times in the database
            query = query.having(story_count >= min_size)
            query = query.order_by(story_count.desc())

        offset = filter_args.get("offset", 0)
        limit = filter_args.get("limit", 20)
        query = query.offset(offset).limit(limit)
        result = db.session.execute(query).tuples()
        return {name: tag_type for name, tag_type, _ in result}

    @classmethod
    def get_all_for_collector(cls):
        return cls.get_filtered(db.select(cls))

    @classmethod
    def get_list(cls, filter_args: dict) -> list[str]:
        tags = cls.get_filtered_tags(filter_args)
        return list(tags.keys())

    @classmethod
    def remove_by_story(cls, story):
        from core.model.news_item import NewsItem

        news_item_ids = db.select(NewsItem.id).where(NewsItem.story_id == story.id)
        tag_keys = cls.get_summary_keys_for_news_item_ids(news_item_ids)
        db.session.execute(db.delete(cls).where(cls.news_item_id.in_(news_item_ids)))
        NewsItemTagCluster.refresh_for_keys(tag_keys)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "tag_type": self.tag_type}

    @classmethod
    def find_by_name(cls, tag_name: str) -> "NewsItemTag | None":
        return cls.get_first(db.select(cls).filter(cls.name.ilike(tag_name)))

    @classmethod
    def apply_sort(cls, query, sort_str: str, *, size_column=None, name_column=None):
        size_column = size_column if size_column is not None else literal_column("size")
        name_column = name_column if name_column is not None else literal_column("name")

        if sort_str == "size_desc":
            return query.order_by(size_column.desc(), name_column.asc())
        elif sort_str == "size_asc":
            return query.order_by(size_column.asc(), name_column.asc())
        elif sort_str == "name_asc":
            return query.order_by(name_column.asc())
        elif sort_str == "name_desc":
            return query.order_by(name_column.desc())

        return query

    @classmethod
    def get_cluster_by_filter(cls, filter_args: dict):
        query = db.select(NewsItemTagCluster.name, NewsItemTagCluster.story_count.label("size"))
        if tag_type := filter_args.get("tag_type"):
            query = query.filter(NewsItemTagCluster.tag_type_key == cls.summary_tag_type_key(tag_type))

        if search := filter_args.get("search"):
            query = query.filter(NewsItemTagCluster.name.ilike(f"%{search}%"))

        count = db.session.execute(db.select(func.count()).select_from(query.subquery())).scalar_one()
        if sort := filter_args.get("sort", "size_desc"):
            query = cls.apply_sort(query, sort, size_column=NewsItemTagCluster.story_count, name_column=NewsItemTagCluster.name)

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
        elif isinstance(tags, list):
            return cls._parse_list_tags(tags)

        logger.warning(f"Invalid tags format: {type(tags).__name__} - expected list or dict")
        return {}

    @classmethod
    def _parse_dict_tags(cls, tags: dict) -> dict[str, "NewsItemTag"]:
        """Parse tags from dict format - handles both old and new formats:
        - Old: {"APT75": "UNKNOWN"}
        - New: {"APT75": {"name": "APT75", "tag_type": "UNKNOWN"}}
        """
        parsed_tags = {}

        for tag_key, tag_data in tags.items():
            if isinstance(tag_data, dict):
                name = tag_data.get("name", tag_key)
                tag_type = tag_data.get("tag_type", "misc")
            elif isinstance(tag_data, str):
                name = tag_key
                tag_type = tag_data
            else:
                raise ValueError(f"Invalid tag format for key '{tag_key}': {type(tag_data).__name__} - must be str or dict")

            if not isinstance(name, str) or not name.strip():
                continue
            name = name.strip()
            tag_type = tag_type if tag_type else "misc"
            parsed_tags[name] = NewsItemTag(name=name, tag_type=tag_type)

        return parsed_tags

    @classmethod
    def _parse_list_tags(cls, tags: list) -> dict[str, "NewsItemTag"]:
        dict_tags = {}
        for tag in tags:
            if isinstance(tag, dict) and "name" in tag:
                dict_tags[tag["name"]] = tag
            elif isinstance(tag, str):
                dict_tags[tag] = {"name": tag, "tag_type": "misc"}
        return cls._parse_dict_tags(dict_tags)

    @classmethod
    def unify_tags(cls, tags: list | dict) -> list[dict[str, str]]:
        """Unify tags to a list of dicts with 'name' and 'tag_type' keys.
        This serves for the __init__ function of NewsItemTag
        """
        if isinstance(tags, dict):
            tags = cls._parse_dict_tags(tags)
        elif isinstance(tags, list):
            tags = cls._parse_list_tags(tags)

        return [{"name": tag.name, "tag_type": tag.tag_type} for tag in tags.values()]

    @staticmethod
    def summary_tag_type_key(tag_type: str | None) -> str:
        return tag_type or ""

    @classmethod
    def get_summary_key(cls, tag_name: str, tag_type: str | None) -> tuple[str, str]:
        return tag_name, cls.summary_tag_type_key(tag_type)

    @classmethod
    def get_summary_keys_for_tag_types(cls, tag_name: str, *tag_types: str | None) -> set[tuple[str, str]]:
        return {cls.get_summary_key(tag_name, tag_type) for tag_type in tag_types if tag_name}

    @classmethod
    def get_summary_keys_for_news_item_ids(cls, news_item_ids) -> set[tuple[str, str]]:
        rows = db.session.execute(
            db.select(cls.name, func.coalesce(cls.tag_type, ""))
            .where(cls.news_item_id.in_(news_item_ids))
            .where(cls.name.is_not(None), cls.name != "")
            .distinct()
        ).all()
        return {(name, tag_type_key) for name, tag_type_key in rows}

    @classmethod
    def get_summary_keys_for_name(cls, tag_name: str) -> set[tuple[str, str]]:
        rows = db.session.execute(
            db.select(cls.name, func.coalesce(cls.tag_type, ""))
            .where(cls.name == tag_name)
            .where(cls.name.is_not(None), cls.name != "")
            .distinct()
        ).all()
        return {(name, tag_type_key) for name, tag_type_key in rows}


class NewsItemTagCluster(BaseModel):
    __tablename__ = "news_item_tag_cluster"
    __table_args__ = (Index("ix_news_item_tag_cluster_type_count", "tag_type_key", "story_count"),)

    name: Mapped[str] = db.Column(db.String(255), primary_key=True)
    tag_type_key: Mapped[str] = db.Column(db.String(255), primary_key=True)
    tag_type: Mapped[str | None] = db.Column(db.String(255), nullable=True)
    news_item_count: Mapped[int] = db.Column(db.Integer, nullable=False, default=0)
    story_count: Mapped[int] = db.Column(db.Integer, nullable=False, default=0)
    last_story_created: Mapped[datetime | None] = db.Column(db.DateTime, nullable=True)

    @classmethod
    def refresh_for_keys(cls, keys: set[tuple[str, str]], session=None) -> None:
        if not keys:
            return
        session = session or db.session
        cls._delete_keys(keys, session=session)
        cls._insert_current_keys(keys, session=session)

    @classmethod
    def rebuild_all(cls, session=None) -> None:
        session = session or db.session
        session.execute(db.delete(cls))
        keys = {
            (name, tag_type_key)
            for name, tag_type_key in session.execute(
                db.select(NewsItemTag.name, func.coalesce(NewsItemTag.tag_type, ""))
                .where(NewsItemTag.name.is_not(None), NewsItemTag.name != "")
                .distinct()
            ).all()
        }
        cls._insert_current_keys(keys, session=session)

    @classmethod
    def _delete_keys(cls, keys: set[tuple[str, str]], session) -> None:
        session.execute(db.delete(cls).where(tuple_(cls.name, cls.tag_type_key).in_(keys)))

    @classmethod
    def _insert_current_keys(cls, keys: set[tuple[str, str]], session) -> None:
        from core.model.news_item import NewsItem
        from core.model.story import Story

        if not keys:
            return
        tag_type_key = func.coalesce(NewsItemTag.tag_type, "")
        rows = session.execute(
            db.select(
                NewsItemTag.name,
                func.min(NewsItemTag.tag_type),
                tag_type_key,
                func.count(func.distinct(NewsItemTag.news_item_id)),
                func.count(func.distinct(NewsItem.story_id)),
                func.max(Story.created),
            )
            .join(NewsItem, NewsItemTag.news_item_id == NewsItem.id)
            .join(Story, NewsItem.story_id == Story.id)
            .where(tuple_(NewsItemTag.name, tag_type_key).in_(keys))
            .where(NewsItemTag.name.is_not(None), NewsItemTag.name != "")
            .group_by(NewsItemTag.name, tag_type_key)
        ).all()
        session.add_all(
            cls(
                name=name,
                tag_type=tag_type,
                tag_type_key=tag_type_key_value,
                news_item_count=news_item_count,
                story_count=story_count,
                last_story_created=last_story_created,
            )
            for name, tag_type, tag_type_key_value, news_item_count, story_count, last_story_created in rows
        )

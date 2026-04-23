from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import func

from core.log import logger
from core.managers.db_manager import db
from core.model.news_item import NewsItem
from core.model.news_item_attribute import NewsItemAttribute
from core.model.news_item_tag import NewsItemTag
from core.model.story import Story


if TYPE_CHECKING:
    from core.model.report_item import ReportItem


class NewsItemTagService:
    @classmethod
    def find_largest_tag_clusters(cls, days: int = 7, limit: int = 12, min_count: int = 2):
        start_date = datetime.now() - timedelta(days=days)

        subquery = (
            db.select(NewsItemTag.name, NewsItemTag.tag_type, Story.id, Story.created)
            .join(NewsItemTag.news_item)
            .join(Story, NewsItem.story_id == Story.id)
            .filter(Story.created >= start_date, NewsItemTag.tag_type.not_ilike("report_%"))
            .distinct()
            .subquery()
        )

        dialect_name = db.session.get_bind().dialect.name
        group_concat_fn = func.group_concat(subquery.c.created) if dialect_name == "sqlite" else func.array_agg(subquery.c.created)

        stmt = (
            db.select(subquery.c.name, subquery.c.tag_type, group_concat_fn, func.count(subquery.c.name).label("count"))
            .select_from(subquery.join(Story, subquery.c.id == Story.id))
            .group_by(subquery.c.name, subquery.c.tag_type)
            .having(func.count(subquery.c.name) >= min_count)
            .order_by(func.count(subquery.c.name).desc())
            .limit(limit)
        )

        result = db.session.execute(stmt).all()
        if not result:
            return []

        results = []
        for name, tag_type, created, count in result:
            published = list(created.split(",")) if dialect_name == "sqlite" else [dt.isoformat() for dt in created]
            results.append(
                {
                    "name": name,
                    "tag_type": tag_type,
                    "published": published,
                    "size": count,
                }
            )

        return results

    @classmethod
    def get_n_biggest_tags_by_type(cls, tag_type: str, n: int, days: int = 0) -> list[dict]:
        story_count = func.count(func.distinct(NewsItem.story_id))
        stmt = (
            db.select(NewsItemTag.name, story_count.label("name_count"))
            .join(NewsItemTag.news_item)
            .filter(NewsItemTag.tag_type == tag_type, NewsItemTag.tag_type.not_ilike("report_%"))
        )

        if days > 0:
            date_threshold = datetime.now() - timedelta(days=days)
            stmt = stmt.join(Story, NewsItem.story_id == Story.id).filter(Story.created >= date_threshold)

        stmt = stmt.group_by(NewsItemTag.name).order_by(story_count.desc()).limit(n)

        result = db.session.execute(stmt).all()
        return [{"name": row[0], "size": row[1]} for row in result]

    @classmethod
    def get_tag_types(cls) -> list[str]:
        items = db.session.execute(
            db.select(NewsItemTag.tag_type)
            .join(NewsItemTag.news_item)
            .where(NewsItemTag.tag_type.not_ilike("report_%"))
            .group_by(NewsItemTag.tag_type)
            .order_by(func.count(func.distinct(NewsItem.story_id)).desc())
        ).all()
        return [row[0] for row in items] if items else []

    @classmethod
    def get_largest_tag_types(cls, days: int) -> dict:
        tag_types = cls.get_tag_types()
        largest_tag_types = {}
        for tag_type in tag_types:
            if tags := cls.get_n_biggest_tags_by_type(tag_type, 5, days=days):
                cluster_size = sum(tag["size"] for tag in tags)
                largest_tag_types[tag_type] = {"size": cluster_size, "tags": tags, "name": tag_type}

        logger.debug(f"Found {len(largest_tag_types)} tag clusters")
        return largest_tag_types

    @classmethod
    def add_report_attribute(cls, story: "Story", report: "ReportItem"):
        story.upsert_attribute(NewsItemAttribute(key=f"report_{report.id}", value=report.title))

    @staticmethod
    def set_found_bot_tags(found_tags: dict[str, Any], change_by_bot: bool = False):
        errors = {}
        for news_item_id, tags in found_tags.items():
            if not tags:
                continue
            news_item = NewsItem.get(news_item_id)
            if not news_item:
                errors[news_item_id] = "News item not found"
                continue
            news_item.set_tags(tags, change_by_bot=change_by_bot)

    @staticmethod
    def set_worker_execution_attribute(*, worker_type: str, worker_id: str, found_tags: dict[str, Any]):
        now = datetime.now().isoformat()
        tag_counts_by_story: dict[str, int] = {}
        stories_by_id: dict[str, Story] = {}

        for news_item_id, tags in found_tags.items():
            if news_item := NewsItem.get(news_item_id):
                if story := news_item.story:
                    stories_by_id[story.id] = story
                    tag_counts_by_story[story.id] = tag_counts_by_story.get(story.id, 0) + len(tags)

        for story_id, tag_count in tag_counts_by_story.items():
            story = stories_by_id[story_id]
            attribute_value = f"worker_id={worker_id}|count={tag_count}|{now}"
            story.upsert_attribute(NewsItemAttribute(key=f"{worker_type}", value=attribute_value))
            story.record_revision(note="set_worker_execution_attribute")

        db.session.commit()

    @classmethod
    def remove_report_attribute(cls, story: "Story", report_id: str):
        story.remove_attributes([f"report_{report_id}"])

    @classmethod
    def delete_tags_by_name(cls, tag_name: str):
        # TODO: Record StoryRevision entries for affected stories before bulk tag deletion.
        db.session.execute(db.delete(NewsItemTag).where(NewsItemTag.name == tag_name))
        db.session.commit()

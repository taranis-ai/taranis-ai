from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func

from core.log import logger
from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.news_item import NewsItem
from core.model.news_item_attribute import NewsItemAttribute
from core.model.news_item_tag import NewsItemTag, NewsItemTagCluster
from core.model.story import Story


class NewsItemTagService:
    @classmethod
    def find_largest_tag_clusters(cls, days: int = 7, limit: int = 12, min_count: int = 2):
        start_date = BaseModel.utcnow() - timedelta(days=days)

        subquery = (
            db.select(NewsItemTag.name, NewsItemTag.tag_type, Story.id, Story.created)
            .join(NewsItemTag.news_item)
            .join(Story, NewsItem.story_id == Story.id)
            .filter(Story.created >= start_date)
            .distinct()
            .subquery()
        )

        dialect_name = db.session.get_bind().dialect.name
        group_concat_fn = func.group_concat(subquery.c.created) if dialect_name == "sqlite" else func.array_agg(subquery.c.created)

        stmt = (
            db.select(subquery.c.name, subquery.c.tag_type, group_concat_fn, func.count(subquery.c.name).label("count"))
            .select_from(subquery)
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
            db.select(NewsItemTag.name, story_count.label("name_count")).join(NewsItemTag.news_item).filter(NewsItemTag.tag_type == tag_type)
        )

        if days > 0:
            date_threshold = BaseModel.utcnow() - timedelta(days=days)
            stmt = stmt.join(Story, NewsItem.story_id == Story.id).filter(Story.created >= date_threshold)

        stmt = stmt.group_by(NewsItemTag.name).order_by(story_count.desc()).limit(n)

        result = db.session.execute(stmt).all()
        return [{"name": row[0], "size": row[1]} for row in result]

    @classmethod
    def get_tag_types(cls) -> list[str]:
        items = db.session.execute(
            db.select(NewsItemTagCluster.tag_type)
            .where(NewsItemTagCluster.tag_type_key != "")
            .group_by(NewsItemTagCluster.tag_type, NewsItemTagCluster.tag_type_key)
            .order_by(func.sum(NewsItemTagCluster.story_count).desc())
        ).all()
        return [row[0] for row in items] if items else []

    @classmethod
    def get_largest_tag_types(cls, days: int) -> dict:
        start_date = BaseModel.utcnow() - timedelta(days=days) if days > 0 else None
        stmt = db.select(
            NewsItemTagCluster.tag_type,
            NewsItemTagCluster.tag_type_key,
            NewsItemTagCluster.name,
            NewsItemTagCluster.story_count,
        ).where(NewsItemTagCluster.tag_type_key != "")
        if start_date:
            stmt = stmt.where(NewsItemTagCluster.last_story_created >= start_date)

        stmt = stmt.order_by(NewsItemTagCluster.tag_type_key, NewsItemTagCluster.story_count.desc())

        largest_tag_types = {}
        for tag_type, tag_type_key, tag_name, story_count in db.session.execute(stmt).all():
            cluster = largest_tag_types.setdefault(tag_type_key, {"size": 0, "tags": [], "name": tag_type})
            if len(cluster["tags"]) >= 5:
                continue
            tag = {"name": tag_name, "size": story_count}
            cluster["tags"].append(tag)
            cluster["size"] += story_count

        logger.debug(f"Found {len(largest_tag_types)} tag clusters")
        return dict(sorted(largest_tag_types.items(), key=lambda item: item[1]["size"], reverse=True))

    @staticmethod
    def set_found_bot_tags(found_tags: dict[str, Any], *, actor: str | None = None):
        errors = {}
        for news_item_id, tags in found_tags.items():
            if not tags:
                continue
            news_item = NewsItem.get(news_item_id)
            if not news_item:
                errors[news_item_id] = "News item not found"
                continue
            news_item.set_tags(tags, actor=actor, replace=False)

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
    def delete_tags_by_name(cls, tag_name: str):
        # TODO: Record StoryRevision entries for affected stories before bulk tag deletion.
        tag_keys = NewsItemTag.get_summary_keys_for_name(tag_name)
        db.session.execute(db.delete(NewsItemTag).where(NewsItemTag.name == tag_name))
        NewsItemTagCluster.refresh_for_keys(tag_keys)
        db.session.commit()

from sqlalchemy import func
from datetime import datetime, timedelta

from core.model.story import Story
from core.model.news_item_tag import NewsItemTag
from core.managers.db_manager import db
from core.log import logger


class NewsItemTagService:
    @classmethod
    def find_largest_tag_clusters(cls, days: int = 7, limit: int = 12, min_count: int = 2):
        start_date = datetime.now() - timedelta(days=days)

        subquery = (
            db.select(NewsItemTag.name, NewsItemTag.tag_type, Story.id, Story.created)
            .join(NewsItemTag.story)
            .filter(Story.created >= start_date)
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
        stmt = db.select(NewsItemTag.name, func.count(NewsItemTag.name).label("name_count")).filter(NewsItemTag.tag_type == tag_type)

        if days > 0:
            date_threshold = datetime.now() - timedelta(days=days)
            stmt = stmt.join(Story, NewsItemTag.story_id == Story.id).filter(Story.created >= date_threshold)

        stmt = stmt.group_by(NewsItemTag.name).order_by(func.count(NewsItemTag.name).desc()).limit(n)

        result = db.session.execute(stmt).all()
        return [{"name": row[0], "size": row[1]} for row in result]

    @classmethod
    def get_largest_tag_types(cls, days: int) -> list:
        tag_types_with_count = NewsItemTag.get_tag_types()
        logger.debug(f"Tag types with count: {tag_types_with_count}")
        largest_tag_types = []
        for tag_type, count in tag_types_with_count:
            if tags := cls.get_n_biggest_tags_by_type(tag_type, 5, days=days):
                largest_tag_types.append({"size": count, "name": tag_type, "tags": tags})

        return largest_tag_types

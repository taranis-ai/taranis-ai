from datetime import datetime, timedelta
from core.model.story import Story
from core.model.news_item_tag import NewsItemTag
from core.managers.db_manager import db
from sqlalchemy import func
from core.log import logger


class NewsItemTagService:
    @classmethod
    def find_largest_tag_clusters(cls, days: int = 7, limit: int = 12, min_count: int = 2):
        start_date = datetime.now() - timedelta(days=days)

        subquery = (
            db.select(NewsItemTag.name, NewsItemTag.tag_type, Story.id, Story.created)
            .join(NewsItemTag.n_i_a)
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
    def get_largest_tag_types(cls) -> dict:
        tag_types_with_count = NewsItemTag.get_tag_types()
        logger.debug(tag_types_with_count)
        return {
            tag_type: {"size": count, "name": tag_type, "tags": NewsItemTag.get_n_biggest_tags_by_type(tag_type, 5)}
            for tag_type, count in tag_types_with_count
        }

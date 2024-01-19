from datetime import datetime, timedelta
from core.model.news_item import NewsItemAggregate
from core.model.news_item_tag import NewsItemTag
from core.managers.db_manager import db
from sqlalchemy import func


class NewsItemTagService:
    @classmethod
    def find_largest_tag_clusters(cls, days: int = 7, limit: int = 12, min_count: int = 2):
        start_date = datetime.now() - timedelta(days=days)
        subquery = (
            db.session.query(NewsItemTag.name, NewsItemTag.tag_type, NewsItemAggregate.id, NewsItemAggregate.created)
            .join(NewsItemTag.n_i_a)
            .filter(NewsItemAggregate.created >= start_date)
            .subquery()
        )

        if db.session.get_bind().dialect.name == "sqlite":
            group_concat_fn = func.group_concat(subquery.c.created)
        else:
            group_concat_fn = func.array_agg(subquery.c.created)

        clusters = (
            db.session.query(subquery.c.name, subquery.c.tag_type, group_concat_fn, func.count(subquery.c.name).label("count"))
            .select_from(subquery.join(NewsItemAggregate, subquery.c.id == NewsItemAggregate.id))
            .group_by(subquery.c.name, subquery.c.tag_type)
            .having(func.count(subquery.c.name) >= min_count)
            .order_by(func.count(subquery.c.name).desc())
            .limit(limit)
            .all()
        )
        if not clusters:
            return []
        results = []
        for cluster in clusters:
            if db.session.get_bind().dialect.name == "sqlite":
                published = list(cluster[2].split(","))
            else:
                published = [dt.isoformat() for dt in cluster[2]]

            results.append(
                {
                    "name": cluster[0],
                    "tag_type": cluster[1],
                    "published": published,
                    "size": cluster[3],
                }
            )
        return results

    @classmethod
    def get_largest_tag_types(cls) -> dict:
        tag_types_with_count = NewsItemTag.get_tag_types()
        return {
            tag_type: {"size": count, "name": tag_type, "tags": NewsItemTag.get_n_biggest_tags_by_type(tag_type, 5)}
            for tag_type, count in tag_types_with_count
        }

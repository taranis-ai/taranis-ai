import json
from datetime import datetime, timedelta
from typing import Sequence
from sqlalchemy import func, Row
from core.model.story import Story
from core.model.news_item import NewsItem
from core.managers.db_manager import db


class StoryService:
    @classmethod
    def extract_stories(cls, result: Sequence[Row]) -> list[dict]:
        stories = {}

        for row in result:
            stories[row.id] = {
                "id": row.id,
                "news_items": [],
            }

            if hasattr(row, "news_item_id"):
                stories[row.id]["news_items"].append(
                    {
                        "id": row.news_item_id,
                        "title": row.news_item_title,
                        "content": row.news_item_content,
                    }
                )

        return list(stories.values())

    @classmethod
    def export(cls) -> bytes:
        query = db.select(
            Story.id,
            Story.news_items,
            NewsItem.id.label("news_item_id"),
            NewsItem.title.label("news_item_title"),
            NewsItem.content.label("news_item_content"),
        ).outerjoin(NewsItem, NewsItem.story_id == Story.id)
        result = db.session.execute(query).all()
        stories = cls.extract_stories(result)
        return json.dumps(stories).encode("utf-8")

    @classmethod
    def export_with_metadata(cls) -> bytes:
        query = db.select(Story).group_by(Story.id).join(NewsItem, NewsItem.story_id == Story.id)
        result: Sequence[Story] = db.session.execute(query).scalars().all()
        stories = [story.to_dict() for story in result]
        return json.dumps(stories).encode("utf-8")

    @classmethod
    def get_story_clusters(cls, days: int = 7, limit: int = 10):
        start_date = datetime.now() - timedelta(days=days)
        if clusters := Story.get_filtered(
            db.select(cls)
            .join(NewsItem)
            .filter(NewsItem.published >= start_date)
            .group_by(Story.title, Story.id)
            .order_by(func.count().desc())
            .having(func.count() > 1)
            .limit(limit)
        ):
            return [
                {
                    "name": cluster.title,
                    "size": len(cluster.news_items),
                    "published": [ni.published.isoformat() for ni in cluster.news_items],
                }
                for cluster in clusters
            ]
        return []

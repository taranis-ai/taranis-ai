import json
from datetime import datetime, timedelta
from typing import Any, Sequence

from flask import Response, abort, jsonify
from sqlalchemy import Row, func

from core.managers import queue_manager
from core.managers.db_manager import db
from core.model.news_item import NewsItem
from core.model.story import Story
from core.model.user import User


class StoryService:
    @classmethod
    def extract_stories(cls, result: Sequence[Row]) -> list[dict]:
        stories: dict[str, dict] = {}

        for row in result:
            if getattr(row, "news_item_id", None) is None:
                continue
            story = stories.setdefault(row.id, {"id": row.id, "created": row.created.astimezone().isoformat(), "news_items": []})

            story["news_items"].append(
                {
                    "id": row.news_item_id,
                    "title": row.news_item_title,
                    "content": row.news_item_content,
                }
            )

        return list(stories.values())

    @classmethod
    def export(cls, time_from: datetime | None, time_to: datetime | None) -> bytes:
        query = db.select(
            Story.id,
            Story.created,
            NewsItem.id.label("news_item_id"),
            NewsItem.title.label("news_item_title"),
            NewsItem.content.label("news_item_content"),
        ).outerjoin(NewsItem, NewsItem.story_id == Story.id)

        if time_from is not None:
            query = query.where(Story.created >= time_from)
        if time_to is not None:
            query = query.where(Story.created <= time_to)

        result = db.session.execute(query).all()
        stories = cls.extract_stories(result)
        return json.dumps(stories).encode("utf-8")

    @classmethod
    def export_with_metadata(cls, time_from: datetime | None, time_to: datetime | None) -> bytes:
        query = db.select(Story).join(NewsItem, NewsItem.story_id == Story.id)

        if time_from is not None:
            query = query.where(Story.created >= time_from)
        if time_to is not None:
            query = query.where(Story.created <= time_to)
        stories: list[Story] = list(db.session.execute(query).scalars().unique().all())
        payload = [story.to_dict() for story in stories]
        return json.dumps(payload).encode("utf-8")

    @classmethod
    def get_story_clusters(cls, days: int = 7, limit: int = 10):
        start_date = datetime.now() - timedelta(days=days)
        if clusters := Story.get_filtered(
            db.select(Story)
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

    @staticmethod
    def update_search_vector(force: bool = False) -> int:
        condition = "" if force else "WHERE s.search_vector = ''::tsvector"

        query = f"""
            UPDATE story AS s
            SET search_vector = fts_build_story_search_vector(s.id::text)
            {condition}
            RETURNING s.id
        """

        result = db.session.execute(db.text(query))
        updated_ids = result.scalars().all()
        db.session.commit()

        return len(updated_ids)

    @staticmethod
    def delete_stories_with_no_items() -> int:
        query = db.delete(Story).where(~db.exists().where(NewsItem.story_id == Story.id)).returning(Story.id)

        result = db.session.execute(query)
        deleted_ids = result.scalars().all()
        db.session.commit()

        return len(deleted_ids)

    @staticmethod
    def fetch_and_create_story(parameters: dict[str, str]):
        return queue_manager.queue_manager.fetch_single_news_item(parameters=parameters)

    @staticmethod
    def _import_story_list(json_data: list[dict[str, Any]], user: User) -> Response:
        """
        Import a list of stories from JSON data.
        """
        imported_stories = []
        for story_data in json_data:
            story = Story.from_dict(story_data)
            db.session.add(story)
            imported_stories.append(story)
        db.session.commit()
        return jsonify({"imported_stories": [story.to_dict() for story in imported_stories]})

    @staticmethod
    def _import_news_item_list(json_data: list[dict[str, Any]], user: User) -> Response:
        """
        Import a list of news items from JSON data.
        """
        imported_news_items = []
        for news_item_data in json_data:
            news_item = NewsItem.from_dict(news_item_data)
            db.session.add(news_item)
            imported_news_items.append(news_item)
        db.session.commit()
        return jsonify({"imported_news_items": [news_item.to_dict() for news_item in imported_news_items]})

    @staticmethod
    def import_stories(json_data: dict[str, Any] | list[dict[str, Any]], user: User) -> Response:
        """
        Import stories or news items from JSON data. Could be either a single story or a list of stories as well as a single news item or a list of news items.
        """
        if isinstance(json_data, list):
            if "news_items" in json_data[0]:
                return StoryService._import_story_list(json_data=json_data, user=user)
            elif "source" in json_data[0]:
                return StoryService._import_news_item_list(json_data=json_data, user=user)
        else:
            if "news_items" in json_data:
                return StoryService._import_story_list(json_data=[json_data], user=user)
            elif "source" in json_data:
                return StoryService._import_news_item_list(json_data=[json_data], user=user)
        abort(400, description="Invalid JSON data for import.")

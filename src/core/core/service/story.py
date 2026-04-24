import json
from datetime import datetime, timedelta
from typing import Any, Sequence

from flask import Response, abort, jsonify
from flask_jwt_extended import current_user
from sqlalchemy import Row, bindparam, func

from core.log import logger
from core.managers import queue_manager
from core.managers.db_manager import db
from core.model.news_item import NewsItem
from core.model.revision import StoryRevision
from core.model.story import Story
from core.model.user import User
from core.service.cache_invalidation import invalidate_frontend_cache_on_success


class StoryService:
    @classmethod
    def extract_stories(cls, result: Sequence[Row]) -> list[dict]:
        stories: dict[str, dict] = {}

        for row in result:
            if getattr(row, "news_item_id", None) is None:
                continue
            story = stories.setdefault(row.id, {"id": row.id, "created": row.created.isoformat(), "news_items": []})

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
    def _prepare_rebuild_search_vector_args(story_ids: Sequence[str] | None) -> tuple[bool, list[str]]:
        if db.engine.dialect.name != "postgresql":
            return False, []

        normalized_story_ids = [story_id for story_id in (story_ids or []) if story_id]
        if story_ids is not None and not normalized_story_ids:
            return False, []

        return True, normalized_story_ids

    @staticmethod
    def _build_rebuild_search_vector_statement(force: bool, story_ids: list[str]) -> tuple[Any, dict[str, Any]]:
        conditions: list[str] = []
        parameters: dict[str, Any] = {}

        if not force:
            conditions.append("s.search_vector = ''::tsvector")
        if story_ids:
            conditions.append("s.id IN :story_ids")
            parameters["story_ids"] = story_ids

        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            UPDATE story AS s
            SET search_vector = fts_build_story_search_vector(s.id)
            {where_sql}
            RETURNING s.id
        """

        statement = db.text(query)
        if story_ids:
            statement = statement.bindparams(bindparam("story_ids", expanding=True))

        return statement, parameters

    @staticmethod
    def rebuild_search_vectors(force: bool = False, story_ids: Sequence[str] | None = None, commit: bool = True) -> int:
        can_update, normalized_story_ids = StoryService._prepare_rebuild_search_vector_args(story_ids)
        if not can_update:
            return 0

        statement, parameters = StoryService._build_rebuild_search_vector_statement(force, normalized_story_ids)

        db.session.flush()
        result = db.session.execute(statement, parameters)
        updated_ids = result.scalars().all()
        if commit:
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
    def fetch_and_create_story(parameters: dict[str, Any]) -> tuple[dict[str, Any], int]:
        result = queue_manager.queue_manager.fetch_single_news_item(parameters=parameters)
        if isinstance(result, tuple):
            return result
        if isinstance(result, list):
            return Story.add_news_items(result)
        if isinstance(result, dict):
            return result, 400 if "error" in result else 200
        if isinstance(result, str):
            return {"message": result}, 200
        return {"error": "Couldn't create News Item"}, 400

    @staticmethod
    def _import_story_list(json_data: list[dict[str, Any]], user: User) -> Response:
        """
        Import a list of stories from JSON data.
        """
        try:
            imported_stories = []
            for story_data in json_data:
                story = Story.from_dict(story_data)
                db.session.add(story)
                story.record_revision(user, note="created")
                imported_stories.append(story)
            db.session.commit()
            invalidate_frontend_cache_on_success(200, full=True)
        except Exception:
            db.session.rollback()
            logger.exception("Failed to import stories")
            abort(400, description="Failed to import stories")
        return jsonify({"imported_stories": [story.to_dict() for story in imported_stories]})

    @staticmethod
    def _import_news_item_list(json_data: list[dict[str, Any]], user: User) -> Response:
        """
        Import a list of news items from JSON data.
        """
        try:
            imported_news_items = []
            for news_item_data in json_data:
                news_item = NewsItem.from_dict(news_item_data)
                db.session.add(news_item)
                imported_news_items.append(news_item)
            db.session.commit()
            invalidate_frontend_cache_on_success(200, full=True)
        except Exception:
            db.session.rollback()
            logger.exception("Failed to import news items")
            abort(400, description="Failed to import news items")
        return jsonify({"imported_news_items": [news_item.to_dict() for news_item in imported_news_items]})

    @staticmethod
    def _get_import_payload_kind(item: Any) -> str | None:
        if not isinstance(item, dict):
            return None

        has_story_fields = "news_items" in item
        has_news_item_fields = "source" in item
        if has_story_fields == has_news_item_fields:
            return None
        return "story" if has_story_fields else "news_item"

    @staticmethod
    def import_stories(json_data: dict[str, Any] | list[dict[str, Any]], user: User) -> Response:
        """
        Import stories or news items from JSON data. Could be either a single story or a list of stories as well as a single news item or a list of news items.
        """
        if not isinstance(json_data, list):
            json_data = [json_data]
        if not json_data:
            abort(400, description="Invalid JSON data for import.")

        payload_kinds = {StoryService._get_import_payload_kind(item) for item in json_data}
        if payload_kinds == {"story"}:
            return StoryService._import_story_list(json_data=json_data, user=user)
        if payload_kinds == {"news_item"}:
            return StoryService._import_news_item_list(json_data=json_data, user=user)
        if None in payload_kinds:
            abort(400, description="Invalid JSON data for import.")
        abort(400, description="Cannot mix story and news item imports.")

    @staticmethod
    def _serialize_revision(revision: StoryRevision, include_data: bool = False) -> dict[str, Any]:
        payload = {
            "id": revision.id,
            "revision": revision.revision,
            "created_at": revision.created_at.isoformat() if revision.created_at else None,
            "created_by": revision.created_by.username if revision.created_by else None,
            "created_by_id": revision.created_by_id,
            "note": revision.note,
        }
        if include_data:
            payload["data"] = revision.data
        return payload

    @classmethod
    def get_story_revisions(cls, story_id: str) -> tuple[dict[str, Any], int]:
        access_response, access_status = Story.get_for_api(story_id, current_user)
        if access_status != 200:
            return access_response, access_status

        revisions = (
            db.session.execute(db.select(StoryRevision).filter(StoryRevision.story_id == story_id).order_by(StoryRevision.revision.desc()))
            .scalars()
            .all()
        )

        return {"total_count": len(revisions), "items": [cls._serialize_revision(revision) for revision in revisions]}, 200

    @classmethod
    def get_story_revision_data(cls, story_id: str, revision_number: int) -> tuple[dict[str, Any], int]:
        access_response, access_status = Story.get_for_api(story_id, current_user)
        if access_status != 200:
            return access_response, access_status

        if revision := db.session.execute(
            db.select(StoryRevision).filter(StoryRevision.story_id == story_id).filter(StoryRevision.revision == revision_number)
        ).scalar_one_or_none():
            return cls._serialize_revision(revision, include_data=True), 200

        return {"error": "Revision not found"}, 404

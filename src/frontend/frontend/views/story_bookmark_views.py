from typing import Any

from flask import abort, make_response, render_template, request, url_for
from flask.typing import ResponseReturnValue
from models.assess import StoryBookmark
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

from frontend.auth import auth_required
from frontend.cache_models import CacheObject, PagingData
from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.utils.router_helpers import is_htmx_request, parse_paging_data
from frontend.utils.validation_helpers import format_pydantic_errors
from frontend.views.base_view import BaseView
from frontend.views.story_views import StoryView


DEFAULT_BOOKMARK_COLLECTION_NAME = "Bookmarks"


class StoryBookmarkView(BaseView):
    model = StoryBookmark
    icon = "bookmark"
    htmx_list_template = "bookmarks/bookmark_list.html"
    default_template = "bookmarks/index.html"
    base_route = "assess.bookmarks"

    @classmethod
    def model_plural_name(cls) -> str:
        return "story_bookmarks"

    @classmethod
    def _response_status(cls, response) -> int:
        return getattr(response, "status_code", 500) or 500

    @classmethod
    def _invalidate_bookmark_cache(cls, bookmark_id: str | None = None) -> None:
        try:
            DataPersistenceLayer().invalidate_model_cache_locally(StoryBookmark, bookmark_id)
        except HTTPException:
            raise
        except ValueError as exc:
            logger.exception("Failed to invalidate local story bookmark cache: %s", exc)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to invalidate local story bookmark cache")
            return

    @classmethod
    def _load_bookmarks(cls, *, fetch_all: bool = False) -> tuple[CacheObject[StoryBookmark] | None, str | None]:
        try:
            paging_data = PagingData().set_fetch_all() if fetch_all else parse_paging_data()
            return DataPersistenceLayer().get_objects(StoryBookmark, paging_data), None
        except ValidationError as exc:
            logger.exception(format_pydantic_errors(exc, cls.model))
            return None, format_pydantic_errors(exc, cls.model)
        except HTTPException:
            raise
        except ValueError as exc:
            logger.exception("Error retrieving story bookmarks")
            return None, str(exc)

    @classmethod
    def _load_first_bookmark(cls) -> tuple[StoryBookmark | None, str | None]:
        try:
            paging_data = PagingData(limit=1, order="created_asc", query_params={"limit": "1", "order": "created_asc"})
            bookmarks = DataPersistenceLayer().get_objects(StoryBookmark, paging_data)
            return (bookmarks[0] if bookmarks else None), None
        except ValidationError as exc:
            logger.exception(format_pydantic_errors(exc, cls.model))
            return None, format_pydantic_errors(exc, cls.model)
        except HTTPException:
            raise
        except ValueError as exc:
            logger.exception("Error retrieving first story bookmark")
            return None, str(exc)

    @staticmethod
    def _response_json(response) -> dict[str, Any]:
        try:
            payload = response.json()
        except (AttributeError, ValueError):
            return {}
        return payload if isinstance(payload, dict) else {}

    @classmethod
    def _get_or_create_first_bookmark_id(cls) -> tuple[str | None, str | None]:
        bookmark, error = cls._load_first_bookmark()
        if error:
            return None, error
        if bookmark and bookmark.id:
            return bookmark.id, None

        create_response = CoreApi().api_post("/assess/bookmarks", json_data={"name": DEFAULT_BOOKMARK_COLLECTION_NAME})
        cls._invalidate_bookmark_cache()
        payload = cls._response_json(create_response)
        if getattr(create_response, "ok", False):
            bookmark_payload = payload.get("bookmark")
            bookmark_id = payload.get("id") or (bookmark_payload.get("id") if isinstance(bookmark_payload, dict) else None)
            if bookmark_id:
                return str(bookmark_id), None
            return None, "Default bookmark collection was created without an id"

        if cls._response_status(create_response) == 409:
            bookmark, error = cls._load_first_bookmark()
            if error:
                return None, error
            if bookmark and bookmark.id:
                return bookmark.id, None

        return None, str(payload.get("error") or "Failed to create default bookmark collection")

    @classmethod
    def _list_context(cls, error: str | None = None) -> dict[str, Any]:
        bookmarks, load_error = cls._load_bookmarks()
        return {"bookmarks": bookmarks, "error": error or load_error, "routes": {"base_route": url_for("assess.bookmarks")}}

    @classmethod
    def _render_list(cls, notification: str | None = None) -> ResponseReturnValue:
        body = render_template("bookmarks/bookmark_list.html", **cls._list_context())
        return make_response((notification or "") + body, 200)

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def list_view(cls) -> ResponseReturnValue:
        template = "bookmarks/bookmark_list.html" if is_htmx_request() else "bookmarks/index.html"
        context = cls._list_context()
        status = 400 if context.get("error") else 200
        return render_template(template, **context), status

    @classmethod
    def _bookmark_story_context(cls, bookmark: StoryBookmark) -> dict[str, Any]:
        filter_lists = StoryView.get_filter_lists()
        stories = CacheObject(bookmark.stories, total_count=len(bookmark.stories), limit=max(len(bookmark.stories), 1))
        enhanced_stories = StoryView._get_enhanced_stories(stories, list(filter_lists.sources))
        return {
            "bookmark": bookmark,
            "stories": enhanced_stories,
        }

    @classmethod
    def _get_bookmark(cls, bookmark_id: str) -> StoryBookmark:
        bookmark = DataPersistenceLayer().get_object(StoryBookmark, bookmark_id)
        if bookmark is None:
            abort(404)
        return bookmark

    @classmethod
    def _render_detail(cls, bookmark_id: str, notification: str | None = None) -> ResponseReturnValue:
        bookmark = cls._get_bookmark(bookmark_id)
        body = render_template("bookmarks/bookmark_detail.html", **cls._bookmark_story_context(bookmark))
        return make_response((notification or "") + body, 200)

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def detail_view(cls, bookmark_id: str) -> ResponseReturnValue:
        bookmark = cls._get_bookmark(bookmark_id)
        return render_template("bookmarks/detail.html", **cls._bookmark_story_context(bookmark)), 200

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def get_add_dialog(cls) -> ResponseReturnValue:
        story_ids = request.args.getlist("story_ids")
        if not story_ids and (story_id := request.args.get("story_id", "")):
            story_ids = [story_id]
        if not story_ids:
            return cls.render_response_notification({"error": "No stories selected for bookmarking."}), 400

        bookmarks, error = cls._load_bookmarks(fetch_all=True)
        if error:
            return cls.render_response_notification({"error": error}), 500
        return render_template("bookmarks/add_story_dialog.html", bookmarks=bookmarks or [], story_ids=story_ids), 200

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def submit_add_dialog(cls) -> ResponseReturnValue:
        story_ids = request.form.getlist("story_ids")
        if not story_ids:
            return make_response(cls.render_response_notification({"error": "No stories selected for bookmarking."}), 400)

        bookmark_id = request.form.get("bookmark_id", "")
        if request.form.get("mode") == "new":
            create_response = CoreApi().api_post("/assess/bookmarks", json_data={"name": request.form.get("name", "")})
            if not getattr(create_response, "ok", False):
                return make_response(cls.get_notification_from_response(create_response), cls._response_status(create_response))
            cls._invalidate_bookmark_cache()
            bookmark_id = create_response.json().get("id", "")

        if not bookmark_id:
            return make_response(cls.render_response_notification({"error": "No bookmark collection selected."}), 400)

        response = CoreApi().api_post(f"/assess/bookmarks/{bookmark_id}/stories", json_data={"story_ids": story_ids})
        cls._invalidate_bookmark_cache(bookmark_id)
        return make_response(cls.get_notification_from_response(response), cls._response_status(response))

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def instant_bookmark_story(cls, story_id: str) -> ResponseReturnValue:
        bookmark_id, error = cls._get_or_create_first_bookmark_id()
        if error or not bookmark_id:
            return make_response(cls.render_response_notification({"error": error or "No bookmark collection available."}), 500)

        response = CoreApi().api_post(f"/assess/bookmarks/{bookmark_id}/stories", json_data={"story_ids": [story_id]})
        cls._invalidate_bookmark_cache(bookmark_id)
        return make_response(cls.get_notification_from_response(response), cls._response_status(response))

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def create_bookmark(cls) -> ResponseReturnValue:
        response = CoreApi().api_post("/assess/bookmarks", json_data={"name": request.form.get("name", "")})
        cls._invalidate_bookmark_cache()
        return cls._render_list(notification=cls.get_notification_from_response(response))

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def update_bookmark(cls, bookmark_id: str) -> ResponseReturnValue:
        response = CoreApi().api_patch(f"/assess/bookmarks/{bookmark_id}", json_data={"name": request.form.get("name", "")})
        cls._invalidate_bookmark_cache(bookmark_id)
        notification = cls.get_notification_from_response(response)
        if request.form.get("return_to") == "detail":
            return cls._render_detail(bookmark_id, notification=notification)
        return cls._render_list(notification=notification)

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def delete_bookmark(cls, bookmark_id: str) -> ResponseReturnValue:
        response = CoreApi().api_delete(f"/assess/bookmarks/{bookmark_id}")
        cls._invalidate_bookmark_cache(bookmark_id)
        if request.args.get("redirect") == "bookmarks" and getattr(response, "ok", False):
            cls.add_flash_notification(response)
            return cls.redirect_htmx(url_for("assess.bookmarks"))
        return cls._render_list(notification=cls.get_notification_from_response(response))

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def remove_stories(cls, bookmark_id: str) -> ResponseReturnValue:
        story_ids = request.form.getlist("story_ids")
        if not story_ids:
            return cls._render_detail(bookmark_id, notification=cls.render_response_notification({"error": "No stories selected."}))

        response = CoreApi().api_post(f"/assess/bookmarks/{bookmark_id}/stories/remove", json_data={"story_ids": story_ids})
        cls._invalidate_bookmark_cache(bookmark_id)
        return cls._render_detail(bookmark_id, notification=cls.get_notification_from_response(response))

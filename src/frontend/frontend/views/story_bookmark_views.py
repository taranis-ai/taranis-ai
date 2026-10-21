from typing import Any

from flask import abort, make_response, render_template, request, url_for
from flask.typing import ResponseReturnValue
from models.assess import Story, StoryBookmark
from pydantic import ValidationError
from requests import Response
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
    def _response_status(cls, response: Response) -> int:
        return getattr(response, "status_code", 500) or 500

    @classmethod
    def _invalidate_bookmark_cache(cls, bookmark_id: str | None = None) -> None:
        try:
            DataPersistenceLayer().invalidate_model_cache_locally(StoryBookmark, bookmark_id)
            DataPersistenceLayer().invalidate_model_cache_locally(Story)
        except HTTPException:
            raise
        except ValueError:
            logger.exception("Failed to invalidate local story bookmark cache")
        except Exception:
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
        except ValueError:
            logger.exception("Error retrieving story bookmarks")
            return None, "Unable to load bookmark collections. Please try again."

    @staticmethod
    def _response_json(response: Any) -> dict[str, Any]:
        try:
            payload = response.json()
        except AttributeError, ValueError:
            return {}
        return payload if isinstance(payload, dict) else {}

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
    def _bookmark_story_context(cls, bookmark: StoryBookmark, selected_story_ids: list[str] | None = None) -> dict[str, Any]:
        filter_lists = StoryView.get_filter_lists()
        story_ids = bookmark.story_ids
        if story_ids:
            paging_data = PagingData(query_params={"story_ids": story_ids}).set_fetch_all()
            story_results = DataPersistenceLayer().get_objects(Story, paging_data)
            stories_by_id = {story.id: story for story in story_results if story.id}
            ordered_stories = [stories_by_id[story_id] for story_id in story_ids if story_id in stories_by_id]
        else:
            ordered_stories = []
        stories = CacheObject(ordered_stories, total_count=len(ordered_stories), limit=max(len(ordered_stories), 1))
        enhanced_stories = StoryView._get_enhanced_stories(stories, list(filter_lists.sources))
        rendered_story_ids = [story.id for story in enhanced_stories if story.id]
        visible_story_ids = set(rendered_story_ids)
        return {
            "bookmark": bookmark,
            "stories": enhanced_stories,
            "story_ids": rendered_story_ids,
            "selected_story_ids": [story_id for story_id in selected_story_ids or [] if story_id in visible_story_ids],
        }

    @classmethod
    def _get_bookmark(cls, bookmark_id: str) -> StoryBookmark:
        bookmark = DataPersistenceLayer().get_object(StoryBookmark, bookmark_id)
        if bookmark is None:
            abort(404)
            raise RuntimeError("abort did not raise")
        return bookmark

    @classmethod
    def _render_detail(
        cls, bookmark_id: str, notification: str | None = None, selected_story_ids: list[str] | None = None
    ) -> ResponseReturnValue:
        bookmark = cls._get_bookmark(bookmark_id)
        body = render_template(
            "bookmarks/bookmark_detail.html", **cls._bookmark_story_context(bookmark, selected_story_ids=selected_story_ids)
        )
        return make_response((notification or "") + body, 200)

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def detail_view(cls, bookmark_id: str) -> ResponseReturnValue:
        bookmark = cls._get_bookmark(bookmark_id)
        return render_template("bookmarks/detail.html", **cls._bookmark_story_context(bookmark)), 200

    @classmethod
    def _membership_updates(cls, story_ids: list[str]) -> str:
        bookmarks, error = cls._load_bookmarks(fetch_all=True)
        if error:
            return ""
        saved_ids = {story_id for bookmark in bookmarks or [] for story_id in bookmark.story_ids}
        return render_template(
            "bookmarks/updates.html",
            story_ids=list(dict.fromkeys(story_ids)),
            saved_ids=saved_ids,
            bookmark_collections=bookmarks or [],
            assess_bookmark_bar_limit=6,
            include_bookmark_bar=StoryView._get_current_url_path() == url_for("assess.assess"),
        )

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def get_add_dialog(cls) -> ResponseReturnValue:
        story_ids = request.args.getlist("story_ids")
        if not story_ids and (story_id := request.args.get("story_id", "")):
            story_ids = [story_id]
        story_ids = list(dict.fromkeys(story_ids))
        if not story_ids:
            return cls.render_response_notification({"error": "No stories selected for bookmarking."}), 400
        bookmarks, error = cls._load_bookmarks(fetch_all=True)
        if error:
            return cls.render_response_notification({"error": error}), 502
        selected_ids = set(story_ids)
        memberships = {bookmark.id: len(selected_ids.intersection(bookmark.story_ids)) for bookmark in bookmarks or []}
        template = "bookmarks/add_story_dialog.html" if is_htmx_request() else "bookmarks/picker.html"
        return render_template(template, bookmarks=bookmarks or [], story_ids=story_ids, memberships=memberships), 200

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def submit_add_dialog(cls) -> ResponseReturnValue:
        story_ids = request.form.getlist("story_ids")
        if not story_ids:
            return cls.render_response_notification({"error": "No stories selected for bookmarking."}), 400
        payload = {
            "story_ids": story_ids,
            "bookmark_ids": request.form.getlist("bookmark_ids"),
            "remove_bookmark_ids": list(
                set(request.form.getlist("remove_bookmark_ids"))
                | (set(request.form.getlist("original_bookmark_ids")) - set(request.form.getlist("bookmark_ids")))
            ),
            "new_collection_name": request.form.get("name", ""),
            "default_bookmark_id": request.form.get("default_bookmark_id") or None,
        }
        response = CoreApi().api_post("/assess/bookmarks/memberships", json_data=payload)
        if response.ok:
            cls._invalidate_bookmark_cache()
        if not is_htmx_request():
            if not response.ok:
                bookmarks, error = cls._load_bookmarks(fetch_all=True)
                memberships = {bookmark.id: len(set(story_ids).intersection(bookmark.story_ids)) for bookmark in bookmarks or []}
                return render_template(
                    "bookmarks/picker.html",
                    bookmarks=bookmarks or [],
                    story_ids=story_ids,
                    memberships=memberships,
                    submitted_bookmark_ids=payload["bookmark_ids"],
                    selected_default_id=payload["default_bookmark_id"],
                    new_collection_name=payload["new_collection_name"],
                    error=error or cls._response_json(response).get("error") or "Unable to update bookmarks. Please try again.",
                ), cls._response_status(response)
            cls.add_flash_notification(response)
            return cls.redirect_htmx(url_for("assess.bookmark_story", story_ids=story_ids))
        body = cls.get_notification_from_response(response)
        if response.ok:
            body += cls._membership_updates(story_ids)
        return make_response(body, cls._response_status(response))

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def instant_bookmark_story(cls, story_id: str) -> ResponseReturnValue:
        response = CoreApi().api_post("/assess/bookmarks/quick-save", json_data={"story_ids": [story_id]})
        if response.ok:
            cls._invalidate_bookmark_cache()
        if not is_htmx_request():
            cls.add_flash_notification(response)
            return cls.redirect_htmx(url_for("assess.story", story_id=story_id))
        if not response.ok:
            return make_response(cls.get_notification_from_response(response), cls._response_status(response))
        payload = cls._response_json(response)
        bookmark = payload["bookmark"]
        body = render_template(
            "bookmarks/save_notification.html",
            notification={"message": f"Saved to {bookmark['name']}", "class": "alert-success"},
            bookmark=bookmark,
            story_id=story_id,
            can_undo=story_id in payload.get("added_story_ids", []),
        )
        return make_response(body + cls._membership_updates([story_id]), 200)

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def create_bookmark(cls) -> ResponseReturnValue:
        response = CoreApi().api_post("/assess/bookmarks", json_data={"name": request.form.get("name", "")})
        cls._invalidate_bookmark_cache()
        return cls._render_list(notification=cls.get_notification_from_response(response))

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def update_bookmark(cls, bookmark_id: str) -> ResponseReturnValue:
        response = CoreApi().api_patch(
            f"/assess/bookmarks/{bookmark_id}",
            json_data={"is_default": True} if request.form.get("is_default") else {"name": request.form.get("name", "")},
        )
        cls._invalidate_bookmark_cache(bookmark_id)
        notification = cls.get_notification_from_response(response)
        if request.form.get("return_to") == "detail":
            return cls._render_detail(bookmark_id, notification=notification)
        return cls._render_list(notification=notification)

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def reorder_bookmarks(cls) -> ResponseReturnValue:
        response = CoreApi().api_patch("/assess/bookmarks/order", json_data={"bookmark_ids": request.form.getlist("bookmark_ids")})
        cls._invalidate_bookmark_cache()
        return cls._render_list(notification=cls.get_notification_from_response(response))

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

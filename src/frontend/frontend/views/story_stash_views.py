from typing import Any

from flask import abort, make_response, render_template, request, url_for
from flask.typing import ResponseReturnValue
from models.assess import StoryStash
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


class StoryStashView(BaseView):
    model = StoryStash
    icon = "bookmark"
    htmx_list_template = "stashes/stash_list.html"
    default_template = "stashes/index.html"
    base_route = "assess.stashes"

    @classmethod
    def model_plural_name(cls) -> str:
        return "story_stashes"

    @classmethod
    def _response_status(cls, response) -> int:
        return getattr(response, "status_code", 500) or 500

    @classmethod
    def _invalidate_stash_cache(cls, stash_id: str | None = None) -> None:
        try:
            DataPersistenceLayer().invalidate_model_cache_locally(StoryStash, stash_id)
        except Exception:
            logger.exception("Failed to invalidate local story stash cache")

    @classmethod
    def _load_stashes(cls, *, fetch_all: bool = False) -> tuple[CacheObject[StoryStash] | None, str | None]:
        try:
            paging_data = PagingData().set_fetch_all() if fetch_all else parse_paging_data()
            return DataPersistenceLayer().get_objects(StoryStash, paging_data), None
        except ValidationError as exc:
            logger.exception(format_pydantic_errors(exc, cls.model))
            return None, format_pydantic_errors(exc, cls.model)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error retrieving story stashes")
            return None, str(exc)

    @classmethod
    def _list_context(cls, error: str | None = None) -> dict[str, Any]:
        stashes, load_error = cls._load_stashes()
        return {"stashes": stashes, "error": error or load_error, "routes": {"base_route": url_for("assess.stashes")}}

    @classmethod
    def _render_list(cls, notification: str | None = None) -> ResponseReturnValue:
        body = render_template("stashes/stash_list.html", **cls._list_context())
        return make_response((notification or "") + body, 200)

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def list_view(cls) -> ResponseReturnValue:
        template = "stashes/stash_list.html" if is_htmx_request() else "stashes/index.html"
        context = cls._list_context()
        status = 400 if context.get("error") else 200
        return render_template(template, **context), status

    @classmethod
    def _stash_story_context(cls, stash: StoryStash) -> dict[str, Any]:
        filter_lists = StoryView.get_filter_lists()
        stories = CacheObject(stash.stories, total_count=len(stash.stories), limit=max(len(stash.stories), 1))
        enhanced_stories = StoryView._get_enhanced_stories(stories, list(filter_lists.sources))
        return {
            "stash": stash,
            "stories": enhanced_stories,
            "story_ids": [story.id for story in enhanced_stories if getattr(story, "id", None)],
            "selected_story_ids": [],
        }

    @classmethod
    def _get_stash(cls, stash_id: str) -> StoryStash:
        stash = DataPersistenceLayer().get_object(StoryStash, stash_id)
        if stash is None:
            abort(404)
        return stash

    @classmethod
    def _render_detail(cls, stash_id: str, notification: str | None = None) -> ResponseReturnValue:
        stash = cls._get_stash(stash_id)
        body = render_template("stashes/stash_detail.html", **cls._stash_story_context(stash))
        return make_response((notification or "") + body, 200)

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def detail_view(cls, stash_id: str) -> ResponseReturnValue:
        stash = cls._get_stash(stash_id)
        return render_template("stashes/detail.html", **cls._stash_story_context(stash)), 200

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def get_add_dialog(cls) -> ResponseReturnValue:
        story_ids = request.args.getlist("story_ids")
        if not story_ids and (story_id := request.args.get("story_id", "")):
            story_ids = [story_id]
        if not story_ids:
            return cls.render_response_notification({"error": "No stories selected for stashing."}), 400

        stashes, error = cls._load_stashes(fetch_all=True)
        if error:
            return cls.render_response_notification({"error": error}), 500
        return render_template("stashes/add_story_dialog.html", stashes=stashes or [], story_ids=story_ids), 200

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def submit_add_dialog(cls) -> ResponseReturnValue:
        story_ids = request.form.getlist("story_ids")
        if not story_ids:
            return make_response(cls.render_response_notification({"error": "No stories selected for stashing."}), 400)

        stash_id = request.form.get("stash_id", "")
        if request.form.get("mode") == "new":
            create_response = CoreApi().api_post("/assess/stashes", json_data={"name": request.form.get("name", "")})
            if not getattr(create_response, "ok", False):
                return make_response(cls.get_notification_from_response(create_response), cls._response_status(create_response))
            cls._invalidate_stash_cache()
            stash_id = create_response.json().get("id", "")

        if not stash_id:
            return make_response(cls.render_response_notification({"error": "No stash selected."}), 400)

        response = CoreApi().api_post(f"/assess/stashes/{stash_id}/stories", json_data={"story_ids": story_ids})
        cls._invalidate_stash_cache(stash_id)
        return make_response(cls.get_notification_from_response(response), cls._response_status(response))

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def create_stash(cls) -> ResponseReturnValue:
        response = CoreApi().api_post("/assess/stashes", json_data={"name": request.form.get("name", "")})
        cls._invalidate_stash_cache()
        return cls._render_list(notification=cls.get_notification_from_response(response))

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def update_stash(cls, stash_id: str) -> ResponseReturnValue:
        response = CoreApi().api_patch(f"/assess/stashes/{stash_id}", json_data={"name": request.form.get("name", "")})
        cls._invalidate_stash_cache(stash_id)
        notification = cls.get_notification_from_response(response)
        if request.form.get("return_to") == "detail":
            return cls._render_detail(stash_id, notification=notification)
        return cls._render_list(notification=notification)

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def delete_stash(cls, stash_id: str) -> ResponseReturnValue:
        response = CoreApi().api_delete(f"/assess/stashes/{stash_id}")
        cls._invalidate_stash_cache(stash_id)
        if request.args.get("redirect") == "stashes" and getattr(response, "ok", False):
            cls.add_flash_notification(response)
            return cls.redirect_htmx(url_for("assess.stashes"))
        return cls._render_list(notification=cls.get_notification_from_response(response))

    @classmethod
    @auth_required("ASSESS_ACCESS")
    def remove_stories(cls, stash_id: str) -> ResponseReturnValue:
        story_ids = request.form.getlist("story_ids")
        if not story_ids:
            return cls._render_detail(stash_id, notification=cls.render_response_notification({"error": "No stories selected."}))

        response = CoreApi().api_post(f"/assess/stashes/{stash_id}/stories/remove", json_data={"story_ids": story_ids})
        cls._invalidate_stash_cache(stash_id)
        return cls._render_detail(stash_id, notification=cls.get_notification_from_response(response))

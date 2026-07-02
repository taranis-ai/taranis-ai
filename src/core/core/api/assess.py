from urllib.parse import unquote, urlparse

from flask import Blueprint, Flask, request
from flask.views import MethodView
from flask_jwt_extended import current_user
from models.assess import StoryBookmarkCreatePayload, StoryBookmarkOrderPayload, StoryBookmarkStoryPayload, StoryBookmarkUpdatePayload
from pydantic import ValidationError

from core.audit import audit_logger
from core.config import Config
from core.log import logger
from core.managers import queue_manager
from core.managers.auth_manager import auth_required
from core.managers.decorators import extract_args, validate_json
from core.managers.sse_manager import sse_manager
from core.model import connector, news_item, news_item_tag, osint_source, story
from core.model.filter_data import FilterData
from core.model.story_conflict import StoryConflict
from core.service.cache_invalidation import (
    SCOPE_ASSESS_VIEWS,
    SCOPE_STORY_REPORT_VIEWS,
    SCOPE_STORY_VIEWS,
    invalidate_frontend_cache_on_success,
)
from core.service.news_item import NewsItemService
from core.service.simple_web_collector import get_simple_web_collector_url
from core.service.story import StoryService


def _validation_error_response(exc: ValidationError) -> tuple[dict[str, str], int]:
    message = exc.errors()[0].get("msg", "Invalid request payload") if exc.errors() else "Invalid request payload"
    return {"error": str(message)}, 400


class OSINTSourceGroupsList(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        return osint_source.OSINTSourceGroup.get_all_for_assess_api(user=current_user)


class OSINTSourcesList(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        return osint_source.OSINTSource.get_all_for_assess_api(user=current_user)


class NewsItems(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        filter_keys = ["search", "read", "important", "relevant", "in_analyze", "range", "sort"]
        filter_args: dict[str, str | int] = {k: v for k, v in request.args.items() if k in filter_keys}

        filter_args["limit"] = min(int(request.args.get("limit", 20)), 1000)
        page = int(request.args.get("page", 0))
        filter_args["offset"] = min(int(request.args.get("offset", page * filter_args["limit"])), (2**31) - 1)
        return news_item.NewsItem.get_all_for_api(filter_args, user=current_user)

    @auth_required("ASSESS_CREATE")
    @validate_json
    def post(self):
        data_json = request.json
        if not data_json:
            return {"error": "No NewsItems in JSON Body"}, 422

        data_json["osint_source_id"] = "manual"
        result, status = story.Story.add_single_news_item(data_json, current_user)
        sse_manager.news_items_updated()
        invalidate_frontend_cache_on_success(status, scopes=(SCOPE_ASSESS_VIEWS, SCOPE_STORY_REPORT_VIEWS))
        return result, status


class NewsItemFetch(MethodView):
    @staticmethod
    def _is_supported_web_url(url: str) -> bool:
        parsed_url = urlparse(url)
        return parsed_url.scheme in {"http", "https"} and bool(parsed_url.netloc)

    @auth_required("ASSESS_CREATE")
    def post(self):
        request_payload = request.get_json(silent=True)
        if not isinstance(request_payload, dict):
            return {"error": "Couldn't create News Item"}, 400

        parameters = request_payload
        url = get_simple_web_collector_url(parameters)
        if not self._is_supported_web_url(url):
            return {"error": "A valid http or https URL is required"}, 400

        response, status = StoryService.fetch_and_create_story(parameters)
        if 200 <= status < 300:
            sse_manager.news_items_updated()
            invalidate_frontend_cache_on_success(status, scopes=(SCOPE_ASSESS_VIEWS, SCOPE_STORY_REPORT_VIEWS))
        return response, status


class NewsItem(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self, item_id: str):
        return news_item.NewsItem.get_for_api(item_id, current_user)

    @auth_required("ASSESS_UPDATE")
    @validate_json
    def put(self, item_id: str):
        response, code = NewsItemService.update(item_id, request.json, current_user)
        sse_manager.news_items_updated()
        invalidate_frontend_cache_on_success(code, scopes=(SCOPE_ASSESS_VIEWS, SCOPE_STORY_REPORT_VIEWS), object_ids={"news_item": item_id})
        return response, code

    @auth_required("ASSESS_UPDATE")
    @validate_json
    def patch(self, item_id: str):
        response, code = NewsItemService.update(item_id, request.json, current_user)
        sse_manager.news_items_updated()
        invalidate_frontend_cache_on_success(code, scopes=(SCOPE_ASSESS_VIEWS, SCOPE_STORY_REPORT_VIEWS), object_ids={"news_item": item_id})
        return response, code

    @auth_required("ASSESS_DELETE")
    def delete(self, item_id: str):
        response, code = NewsItemService.delete(item_id, current_user)
        sse_manager.news_items_updated()
        invalidate_frontend_cache_on_success(code, scopes=(SCOPE_ASSESS_VIEWS, SCOPE_STORY_REPORT_VIEWS), object_ids={"news_item": item_id})
        return response, code


class UpdateNewsItemAttributes(MethodView):
    @auth_required("ASSESS_UPDATE")
    def put(self, news_item_id: str):
        actor = story.Story.last_change_for_user(current_user)
        response, status = news_item.NewsItem.update_attributes(news_item_id, request.json, actor=actor)
        invalidate_frontend_cache_on_success(status, scopes=(SCOPE_ASSESS_VIEWS,), object_ids={"news_item": news_item_id})
        return response, status


class UpdateNewsItemTags(MethodView):
    @auth_required("ASSESS_UPDATE")
    @validate_json
    def put(self, news_item_id: str):
        item = news_item.NewsItem.get(news_item_id)
        if not item:
            return {"error": "NewsItem not found"}, 404
        if not item.allowed_with_acl(current_user, require_write_access=True):
            return {"error": "User does not have write access to this news item"}, 403

        tags = request.json
        if not isinstance(tags, (list, dict)):
            return {"error": "Tags must be a list or object"}, 400

        response, status = item.set_tags(tags, user=current_user)
        invalidate_frontend_cache_on_success(status, models=("story", "news_item", "report_item"), object_ids={"news_item": news_item_id})
        return response, status


class Stories(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        try:
            filter_keys = [
                "search",
                "read",
                "unread",
                "important",
                "cybersecurity",
                "relevant",
                "in_report",
                "changed_by",
                "range",
                "sort",
                "timefrom",
                "timeto",
                "no_count",
                "exclude_attr",
            ]
            filter_args: dict[str, str | int | list] = {k: v for k, v in request.args.items() if k in filter_keys}
            filter_list_keys = ["source", "group", "story_ids", "language"]
            for key in filter_list_keys:
                filter_args[key] = request.args.getlist(key)

            filter_args["limit"] = min(int(request.args.get("limit", 20)), 400)
            tags = request.args.getlist("tags")
            filter_args["tags"] = [unquote(t) for t in tags]
            page = int(request.args.get("page", 0))
            offset = int(request.args.get("offset", page * filter_args["limit"]))
            filter_args["offset"] = min(offset, (2**31) - 1)

            return story.Story.get_by_filter_json(filter_args, current_user)
        except Exception:
            logger.exception("Failed to get Stories")
            return {"error": "Failed to get Stories"}, 400

    @auth_required("ASSESS_UPDATE")
    def post(self):
        if not (data_json := request.json):
            return {"error": "No story ids provided"}, 400
        story_ids = data_json.get("story_ids")
        payload = data_json.get("payload")
        if not isinstance(story_ids, list) or not story_ids:
            return {"error": "No story ids provided"}, 400
        if payload is not None and not isinstance(payload, dict):
            return {"error": "Invalid payload provided"}, 400

        result_dict = {"message": "Bulk action completed", "updated": 0, "success": [], "errors": []}
        for story_id in story_ids:
            if not story_id:
                continue
            s = story.Story.get(story_id)
            if s is None:
                return {"error": "Story not found"}, 404
            response, code = story.Story.update(s.id, payload, current_user)
            if code != 200:
                result_dict["errors"].append({"story_id": s.id, "response": response})
            else:
                result_dict["success"].append({"story_id": s.id, "response": response})
                result_dict["updated"] += 1

        result_dict["message"] = f"Bulk action completed. {result_dict['updated']} stories updated."
        invalidate_frontend_cache_on_success(200, models=("story",))
        return result_dict, 200


class StoryTagList(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        try:
            search = request.args.get("search", "")
            limit = min(int(request.args.get("limit", 20)), 200)
            offset = min(int(request.args.get("offset", 0)), (2**31) - 1)
            filter_args = {"limit": limit, "offset": offset, "search": search}
            return news_item_tag.NewsItemTag.get_list(filter_args)
        except Exception:
            logger.exception()
            return {"error": "Failed to get Tags"}, 400


class Story(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self, story_id: str):
        return story.Story.get_for_api(story_id, current_user)

    @auth_required("ASSESS_UPDATE")
    @validate_json
    def put(self, story_id):
        response, code = story.Story.update(story_id, request.json, current_user)
        sse_manager.news_items_updated()
        invalidate_frontend_cache_on_success(code, scopes=(SCOPE_STORY_REPORT_VIEWS,), object_ids={"story": story_id})
        return response, code

    @auth_required("ASSESS_DELETE")
    def delete(self, story_id):
        response, code = story.Story.delete_by_id(story_id, current_user)
        sse_manager.news_items_updated()
        invalidate_frontend_cache_on_success(
            code, models=("story_bookmark",), scopes=(SCOPE_STORY_REPORT_VIEWS,), object_ids={"story": story_id}
        )
        return response, code

    @auth_required("ASSESS_UPDATE")
    @validate_json
    def patch(self, story_id):
        response, code = story.Story.update(story_id, request.json, current_user)
        invalidate_frontend_cache_on_success(code, scopes=(SCOPE_STORY_REPORT_VIEWS,), object_ids={"story": story_id})
        return response, code


class UnGroupNewsItem(MethodView):
    @auth_required("ASSESS_UPDATE")
    @validate_json
    def put(self):
        if not (newsitem_ids := request.json):
            return {"error": "No news item ids provided"}, 400
        actor = story.Story.last_change_for_user(current_user)
        response, code = story.Story.ungroup_news_items_from_story(newsitem_ids, current_user, actor=actor)
        sse_manager.news_items_updated()
        invalidate_frontend_cache_on_success(code, scopes=(SCOPE_STORY_VIEWS,))
        return response, code


class UnGroupStories(MethodView):
    @auth_required("ASSESS_UPDATE")
    @validate_json
    def put(self):
        if not (story_ids := request.json):
            return {"error": "No story ids provided"}, 400
        response, code = story.Story.ungroup_multiple_stories(story_ids, current_user)
        sse_manager.news_items_updated()
        invalidate_frontend_cache_on_success(code, scopes=(SCOPE_STORY_VIEWS,))
        return response, code


class GroupAction(MethodView):
    @auth_required("ASSESS_UPDATE")
    @validate_json
    def put(self):
        if not (story_ids := request.json):
            return {"error": "No story ids provided"}, 400
        actor = story.Story.last_change_for_user(current_user)
        response, code = story.Story.group_stories(story_ids, current_user, actor=actor)
        sse_manager.news_items_updated()
        invalidate_frontend_cache_on_success(code, scopes=(SCOPE_STORY_VIEWS,))
        return response, code

    @auth_required("ASSESS_UPDATE")
    @validate_json
    def post(self):
        if not (story_ids := request.json):
            return {"error": "No story ids provided"}, 400
        actor = story.Story.last_change_for_user(current_user)
        response, code = story.Story.group_stories(story_ids, current_user, actor=actor)
        sse_manager.news_items_updated()
        invalidate_frontend_cache_on_success(code, scopes=(SCOPE_STORY_VIEWS,))
        return response, code


class BotActions(MethodView):
    @auth_required("ASSESS_UPDATE")
    @validate_json
    def post(self):
        if not request.json:
            return {"error": "Please provide story_id & bot_id"}, 400
        bot_id = request.json.get("bot_id")
        if not bot_id:
            return {"error": "No bot_id provided"}, 400
        story_id = request.json.get("story_id")
        if not story_id:
            return {"error": "No story_id provided"}, 400
        response, code = queue_manager.queue_manager.execute_bot_task(bot_id=bot_id, filter={"story_id": story_id})
        sse_manager.news_items_updated()
        invalidate_frontend_cache_on_success(code, models=("story",), object_ids={"story": story_id})
        return response, code


class Connectors(MethodView):
    @auth_required("CONNECTOR_USER_ACCESS")
    @extract_args("search", "page", "limit", "offset", "sort", "order", "fetch_all")
    def get(self, connector_id: str | None = None, filter_args: dict | None = None):
        if connector_id:
            return connector.Connector.get_for_api(connector_id)
        return connector.Connector.get_all_for_user_api(filter_args, user=current_user)

    @auth_required("CONNECTOR_USER_ACCESS")
    @validate_json
    def post(self, connector_id: str | None = None):
        """Send stories to an external system."""
        if not connector_id:
            return {"error": "No connector_id provided"}, 400
        if not request.json:
            return {"error": "Invalid JSON payload"}, 400

        story_ids = request.json.get("story_ids")
        if not story_ids:
            return {"error": "No story_id provided"}, 400

        try:
            response, code = queue_manager.queue_manager.push_to_connector(connector_id=connector_id, story_ids=story_ids)
            return response, code
        except Exception:
            logger.exception("Failed to push stories to connector %s", connector_id)
            return {"error": "Failed to push stories to connector"}, 500


class FilterLists(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        return FilterData.get_assess_filterlists(user=current_user), 200


class StoryBookmarks(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        filter_keys = {"search", "page", "limit", "offset", "sort", "order", "fetch_all"}
        filter_args: dict[str, str] = {key: value for key, value in request.args.items() if key in filter_keys}
        return story.StoryBookmark.get_all_for_api(filter_args, current_user)

    @auth_required("ASSESS_ACCESS")
    @validate_json
    def post(self):
        try:
            payload = StoryBookmarkCreatePayload.model_validate(request.json or {})
        except ValidationError as exc:
            return _validation_error_response(exc)

        response, status = story.StoryBookmark.add(payload.model_dump(mode="json"), current_user)
        invalidate_frontend_cache_on_success(status, models=("story_bookmark",))
        return response, status


class StoryBookmark(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self, bookmark_id: str):
        return story.StoryBookmark.get_for_api(bookmark_id, current_user)

    @auth_required("ASSESS_ACCESS")
    @validate_json
    def patch(self, bookmark_id: str):
        try:
            payload = StoryBookmarkUpdatePayload.model_validate(request.json or {})
        except ValidationError as exc:
            return _validation_error_response(exc)

        response, status = story.StoryBookmark.update_for_api(bookmark_id, payload.model_dump(mode="json"), current_user)
        invalidate_frontend_cache_on_success(status, models=("story_bookmark",), object_ids={"story_bookmark": bookmark_id})
        return response, status

    @auth_required("ASSESS_ACCESS")
    def delete(self, bookmark_id: str):
        response, status = story.StoryBookmark.delete_for_api(bookmark_id, current_user)
        invalidate_frontend_cache_on_success(status, models=("story_bookmark",), object_ids={"story_bookmark": bookmark_id})
        return response, status


class StoryBookmarkOrder(MethodView):
    @auth_required("ASSESS_ACCESS")
    @validate_json
    def patch(self):
        try:
            payload = StoryBookmarkOrderPayload.model_validate(request.json or {})
        except ValidationError as exc:
            return _validation_error_response(exc)

        response, status = story.StoryBookmark.reorder_for_api(payload.bookmark_ids, current_user)
        invalidate_frontend_cache_on_success(status, models=("story_bookmark",))
        return response, status


class StoryBookmarkStories(MethodView):
    @auth_required("ASSESS_ACCESS")
    @validate_json
    def post(self, bookmark_id: str):
        try:
            payload = StoryBookmarkStoryPayload.model_validate(request.json or {})
        except ValidationError as exc:
            return _validation_error_response(exc)

        response, status = story.StoryBookmark.add_stories(bookmark_id, payload.story_ids, current_user)
        invalidate_frontend_cache_on_success(status, models=("story_bookmark",), object_ids={"story_bookmark": bookmark_id})
        return response, status


class StoryBookmarkStoryRemoval(MethodView):
    @auth_required("ASSESS_ACCESS")
    @validate_json
    def post(self, bookmark_id: str):
        try:
            payload = StoryBookmarkStoryPayload.model_validate(request.json or {})
        except ValidationError as exc:
            return _validation_error_response(exc)

        response, status = story.StoryBookmark.remove_stories(bookmark_id, payload.story_ids, current_user)
        invalidate_frontend_cache_on_success(status, models=("story_bookmark",), object_ids={"story_bookmark": bookmark_id})
        return response, status


class Proposals(MethodView):
    @auth_required("CONNECTOR_USER_ACCESS")
    def get(self):
        return {"count": StoryConflict.get_proposal_count()}, 200


class StoryRevisions(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self, story_id: str):
        return StoryService.get_story_revisions(story_id)


class StoryRevisionData(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self, story_id: str, revision_number: int):
        return StoryService.get_story_revision_data(story_id, revision_number)


class AssessImport(MethodView):
    @auth_required("ASSESS_CREATE")
    @validate_json
    def post(self):
        if not (data_json := request.json):
            return {"error": "No data provided"}, 400

        imported_stories = StoryService.import_stories(data_json, current_user)
        sse_manager.news_items_updated()
        return imported_stories


def initialize(app: Flask):
    assess_bp = Blueprint("assess", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/assess")

    assess_bp.add_url_rule("/stories", view_func=Stories.as_view("stories"))
    assess_bp.add_url_rule("/bookmarks", view_func=StoryBookmarks.as_view("bookmarks"))
    assess_bp.add_url_rule("/bookmarks/order", view_func=StoryBookmarkOrder.as_view("bookmark_order"))
    assess_bp.add_url_rule("/bookmarks/<string:bookmark_id>", view_func=StoryBookmark.as_view("bookmark"))
    assess_bp.add_url_rule("/bookmarks/<string:bookmark_id>/stories", view_func=StoryBookmarkStories.as_view("bookmark_stories"))
    assess_bp.add_url_rule(
        "/bookmarks/<string:bookmark_id>/stories/remove", view_func=StoryBookmarkStoryRemoval.as_view("bookmark_story_removal")
    )
    assess_bp.add_url_rule("/stories/<string:story_id>", view_func=Story.as_view("story_"))
    assess_bp.add_url_rule("/story/<string:story_id>", view_func=Story.as_view("story"))
    assess_bp.add_url_rule("/story/<string:connector_id>/share", view_func=Connectors.as_view("share_to_connector"))
    assess_bp.add_url_rule("/osint-source-group-list", view_func=OSINTSourceGroupsList.as_view("osint_source_groups-list"))
    assess_bp.add_url_rule("/osint-sources-list", view_func=OSINTSourcesList.as_view("osint_sources_list"))
    assess_bp.add_url_rule("/taglist", view_func=StoryTagList.as_view("taglist"))
    assess_bp.add_url_rule("/filter-lists", view_func=FilterLists.as_view("filter_lists"))
    assess_bp.add_url_rule("/import", view_func=AssessImport.as_view("import"))
    assess_bp.add_url_rule("/news-items", view_func=NewsItems.as_view("news_items"))
    assess_bp.add_url_rule("/news-items/fetch", view_func=NewsItemFetch.as_view("news_item_fetch"))
    assess_bp.add_url_rule("/news-items/<string:item_id>", view_func=NewsItem.as_view("news_item"))
    assess_bp.add_url_rule(
        "/news-items/<string:news_item_id>/attributes", view_func=UpdateNewsItemAttributes.as_view("update_news_item_attributes")
    )
    assess_bp.add_url_rule("/news-items/<string:news_item_id>/tags", view_func=UpdateNewsItemTags.as_view("update_news_item_tags"))
    assess_bp.add_url_rule("/stories/group", view_func=GroupAction.as_view("group_action"))
    assess_bp.add_url_rule("/stories/ungroup", view_func=UnGroupStories.as_view("ungroup_stories"))
    assess_bp.add_url_rule("/news-items/ungroup", view_func=UnGroupNewsItem.as_view("ungroup_news_items"))
    assess_bp.add_url_rule("/stories/botactions", view_func=BotActions.as_view("bot_actions"))
    assess_bp.add_url_rule("/stories/bulk_action", view_func=Stories.as_view("bulk_action"))
    assess_bp.add_url_rule("/connectors", view_func=Connectors.as_view("connectors_list"))
    assess_bp.add_url_rule("/connectors/proposals", view_func=Proposals.as_view("proposals"))
    assess_bp.add_url_rule("/stories/<string:story_id>/revisions", view_func=StoryRevisions.as_view("story_revisions"))
    assess_bp.add_url_rule(
        "/stories/<string:story_id>/revisions/<int:revision_number>",
        view_func=StoryRevisionData.as_view("story_revision_data"),
    )

    assess_bp.after_request(audit_logger.after_request_audit_log)
    app.register_blueprint(assess_bp)

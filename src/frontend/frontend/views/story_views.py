from typing import Any
from flask_jwt_extended import current_user
from flask import json, render_template, request, url_for, make_response, abort, Response
from pydantic import ValidationError
from urllib.parse import urlencode, urlparse, parse_qs

from models.assess import Story, FilterLists, AssessSource, NewsItem, BulkAction, StoryUpdatePayload
from models.report import ReportItem
from models.admin import Connector
from frontend.utils.form_data_parser import parse_formdata
from frontend.views.base_view import BaseView
from frontend.core_api import CoreApi
from frontend.cache import get_model_from_cache, add_model_to_cache
from frontend.auth import auth_required
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.utils.validation_helpers import format_pydantic_errors
from frontend.cache_models import PagingData, CacheObject


class StoryView(BaseView):
    model = Story
    icon = "newspaper"
    htmx_list_template = "assess/story_table.html"
    htmx_update_template = "assess/story.html"
    edit_template = "assess/story_edit.html"
    default_template = "assess/index.html"

    base_route = "assess.assess"
    edit_route = "assess.story_edit"
    _show_sidebar = True

    @classmethod
    def get_extra_context(cls, base_context: dict[str, Any]) -> dict[str, Any]:
        base_context["filter_lists"] = cls._get_filter_lists()
        if stories := base_context.get("stories"):
            enhanced_stories = cls._get_enhanced_stories(stories, list(base_context["filter_lists"].sources))
            base_context["story_ids"] = [story.id for story in enhanced_stories if getattr(story, "id", None)]
            base_context["stories"] = enhanced_stories
        return base_context

    @classmethod
    def model_plural_name(cls) -> str:
        return "stories"

    @classmethod
    def get_sidebar_template(cls) -> str:
        return "assess/assess_sidebar.html"

    @staticmethod
    def _get_enhanced_stories(stories: CacheObject[Story], sources: list[AssessSource]) -> CacheObject[Story]:
        source_dict = {source.id: source for source in sources if source.id}
        return CacheObject(
            [StoryView._enhance_story_with_details(story, source_dict) for story in stories.items],
            total_count=stories.total_count,
            page=stories.page,
            limit=stories.limit,
            order=stories.order,
        )

    @staticmethod
    def _enhance_story_with_details(story: Story, sources: dict[str, Any]) -> Story:
        if not story.news_items:
            return story
        if first_news_item := story.news_items[0]:
            if source := sources.get(first_news_item.osint_source_id):
                # Add the source as an pydantic extra field to the story for easier access in the template
                story.source_info = source  # type: ignore
        return story

    @staticmethod
    def _get_filter_lists() -> FilterLists:
        if filter_lists := get_model_from_cache(FilterLists._model_name, "", current_user.id):
            return filter_lists
        if filter_lists_content := CoreApi().get_filter_lists():
            filter_lists = FilterLists(**filter_lists_content)
            add_model_to_cache(filter_lists, "", current_user.id)
            return filter_lists
        return FilterLists(tags=[], sources=[], groups=[])

    @staticmethod
    def _get_story(story_id: str) -> Story | None:
        if story := get_model_from_cache(Story._model_name, story_id, current_user.id):
            return story
        if story_content := CoreApi().get_story(story_id):
            story = Story(**story_content)
            add_model_to_cache(story, story_id, current_user.id)
            return story
        return None

    @classmethod
    @auth_required()
    def get_sharing_dialog(cls) -> str:
        story_id = request.args.get("story_id", "")
        if story := cls._get_story(story_id):
            connectors = DataPersistenceLayer().get_objects(Connector)
            return render_template("assess/story_sharing_dialog.html", story=story, connectors=connectors)
        return render_template("assess/story_sharing_dialog.html", story=None, connectors=[])

    @classmethod
    @auth_required()
    def submit_sharing_dialog(cls) -> str:
        story_id = request.form.get("story_id", "")
        logger.debug(f"Submitting sharing dialog for story {story_id} - {request.form}")
        return cls.render_response_notification({"message": "Story shared successfully", "category": "success"})

    @classmethod
    @auth_required()
    def get_report_dialog(cls) -> tuple[str, int]:
        story_ids = request.args.getlist("story_ids")
        logger.debug(f"Opening report dialog for stories {story_ids}")
        reports = DataPersistenceLayer().get_objects(ReportItem)
        return render_template("assess/story_report_dialog.html", story_ids=story_ids, reports=reports), 200

    @classmethod
    @auth_required()
    def get_cluster_dialog(cls) -> tuple[str, int]:
        story_ids = request.args.getlist("story_ids")
        logger.debug(f"Opening cluster dialog for stories {story_ids}")
        stories = [s for s in DataPersistenceLayer().get_objects(Story) if s.id in story_ids]
        return render_template("assess/story_grouping_dialog.html", stories=stories), 200

    @classmethod
    @auth_required()
    def submit_cluster_dialog(cls) -> Response:
        story_ids = request.form.getlist("story_ids")
        logger.debug(f"Submitting cluster dialog for stories {story_ids}")
        response = CoreApi().api_post("/assess/stories/group", json_data=story_ids)
        DataPersistenceLayer().invalidate_cache_by_object(Story)
        return cls.rerender_list(notification=cls.get_notification_from_response(response))

    @classmethod
    @auth_required()
    def submit_report_dialog(cls) -> Response:
        story_ids = request.form.getlist("story_ids")
        report_id = request.form.get("report", "")
        response = CoreApi().api_post(f"/analyze/report-items/{report_id}/stories", json_data=story_ids)
        DataPersistenceLayer().invalidate_cache_by_object(Story)
        DataPersistenceLayer().invalidate_cache_by_object(ReportItem)
        return cls.rerender_list(notification=cls.get_notification_from_response(response))

    @classmethod
    @auth_required()
    def bulk_action(cls):
        try:
            payload: dict[str, Any] = {request.form.get("action", ""): request.form.get("value")}
            story_action = StoryUpdatePayload(**payload)
            bulk_action = BulkAction(payload=story_action, story_ids=request.form.getlist("story_ids"))
        except ValidationError:
            logger.debug("No story IDs supplied for bulk update. Returning current story list.")
            return cls.rerender_list(notification=cls.render_response_notification({"error": "No stories selected for bulk action."}))
        response = CoreApi().api_post("/assess/stories/bulk_action", json_data=bulk_action.model_dump(mode="json"))

        DataPersistenceLayer().invalidate_cache_by_object(Story)
        return cls.rerender_list(notification=cls.get_notification_from_response(response))

    @staticmethod
    def parse_paging_data(params: dict[str, list[str]] | None = None) -> PagingData:
        """Unmarshal query parameters into a PagingData model."""
        source_params = params if params is not None else request.args.to_dict(flat=False)
        args: dict[str, list[str]] = {key: list(value) for key, value in source_params.items()}

        # Flatten single-value entries for convenience in query_params
        query_params: dict[str, str | list[str]] = {k: v[0] if len(v) == 1 else v for k, v in args.items()}

        # Extract known parameters (convert to correct types if possible)
        def get_int(value: Any) -> int | None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        page = get_int(query_params.get("page"))
        limit = get_int(query_params.get("limit"))
        order = str(query_params.get("order")) if "order" in query_params else None
        search = str(query_params.get("search")) if "search" in query_params else None

        return PagingData(
            page=page,
            limit=limit,
            order=order,
            search=search,
            query_params=query_params,
        )

    @classmethod
    def _build_pagination_context(
        cls,
        stories: CacheObject[Story] | None,
        paging: PagingData,
        request_params: dict[str, list[str]],
    ) -> dict[str, Any]:
        """
        Prepare pagination metadata and URLs while preserving active filters.
        """
        total_count = stories.total_count if stories else 0
        limit = max(paging.limit or 20, 1)
        total_pages = stories.total_pages if stories else 1

        requested_index = paging.page or 0
        clamped_index = min(max(requested_index, 0), max(total_pages - 1, 0))

        def build_url(page_index: int) -> str:
            params = {key: value[:] for key, value in request_params.items() if value and key != "offset"}
            if page_index <= 0:
                params.pop("page", None)
            else:
                params["page"] = [str(page_index)]
            query_string = urlencode(params, doseq=True)
            base_url = cls.get_base_route()
            return f"{base_url}?{query_string}" if query_string else base_url

        items_on_page = len(stories or [])
        if total_count and items_on_page:
            page_start = clamped_index * limit + 1
            page_end = min(page_start + items_on_page - 1, total_count)
        else:
            page_start = 0
            page_end = 0

        return {
            "infinite_scroll": current_user.profile.infinite_scroll,
            "current_page": clamped_index + 1,
            "total_pages": total_pages,
            "has_previous": clamped_index > 0,
            "has_next": (clamped_index + 1) < total_pages,
            "previous_url": build_url(clamped_index - 1) if clamped_index > 0 else "",
            "next_url": build_url(clamped_index + 1) if (clamped_index + 1) < total_pages else "",
            "page_start": page_start,
            "page_end": page_end,
            "total_count": total_count,
        }

    @classmethod
    def _render_story_list(
        cls,
        paging_data: PagingData,
        request_params: dict[str, list[str]],
    ):
        logger.debug(f"Got request params: {request_params}")
        try:
            items = DataPersistenceLayer().get_objects(cls.model, paging_data=paging_data)
            error = None if items else f"No {cls.model_name()} items found"
        except ValidationError as exc:
            logger.exception(format_pydantic_errors(exc, cls.model))
            items, error = None, format_pydantic_errors(exc, cls.model)
        except Exception as exc:
            logger.exception(f"Error retrieving {cls.model_name()} items")
            items, error = None, str(exc)

        context = cls.get_view_context(items, error)
        context["pagination"] = cls._build_pagination_context(items or None, paging_data, request_params)

        return render_template(cls.get_list_template(), **context), 200

    @classmethod
    def rerender_list(cls, notification: str | None = None):
        request_params = request.args.to_dict(flat=False)

        if request.method == "POST" and "HX-Current-URL" in request.headers:
            url = request.headers.get("HX-Current-URL", "")

            parsed_url = urlparse(url)
            request_params = parse_qs(parsed_url.query)

        paging_data = cls.parse_paging_data(request_params)
        table, status = cls._render_story_list(paging_data, request_params)
        if notification:
            return make_response(notification + table, status)
        return make_response(table, status)

    @classmethod
    def list_view(cls):
        request_params = request.args.to_dict(flat=False)
        paging_data = cls.parse_paging_data(request_params)
        return cls._render_story_list(paging_data, request_params)

    @classmethod
    def get_item_context(cls, object_id: int | str) -> dict[str, Any]:
        context = super().get_item_context(object_id)
        context["_show_sidebar"] = False
        context["form_action"] = f"hx-post={url_for('assess.story_edit', story_id=object_id)}"
        story = context.get("story")

        if isinstance(story, Story):
            attributes = story.attributes or []
            context["has_rt_id"] = any(isinstance(attr, dict) and attr.get("key") == "rt_id" for attr in attributes)

            cybersecurity_value = next(
                (attr.get("value") for attr in attributes if isinstance(attr, dict) and attr.get("key") == "cybersecurity"),
                None,
            )
            context["story_cyber_status"] = cls._format_cyber_status(cybersecurity_value)
            context["cyber_chip_class"] = cls._get_cyber_chip_class(context["story_cyber_status"])
        else:
            context["has_rt_id"] = False
            context["story_cyber_status"] = "Not Classified"
            context["cyber_chip_class"] = "badge badge-outline"

        return context

    @staticmethod
    def _format_cyber_status(status: str | None) -> str:
        if not status:
            return "Not Classified"
        normalized = status.strip().lower()
        labels = {
            "yes": "Yes",
            "no": "No",
            "mixed": "Mixed",
            "incomplete": "Incomplete",
            "none": "Not Classified",
        }
        return labels.get(normalized, normalized.capitalize())

    @staticmethod
    def _get_cyber_chip_class(status: str) -> str:
        mapping = {
            "Yes": "badge badge-success badge-lg",
            "No": "badge badge-error badge-lg",
            "Mixed": "badge badge-secondary badge-lg",
            "Incomplete": "badge badge-warning badge-lg",
            "Not Classified": "badge badge-outline badge-lg",
        }
        return mapping.get(status, "badge badge-outline badge-lg")

    @classmethod
    @auth_required()
    def story_view(cls, story_id: str):
        return render_template("assess/story_view.html", **cls.get_item_context(story_id)), 200

    @classmethod
    def update_from_form(cls, story_id: str):
        core_response, error = cls.process_form_data(story_id)
        if error or not core_response:
            error_payload = error if isinstance(error, dict) else {"error": error or "Failed to update story."}
            notification_html = render_template(
                "notification/index.html",
                notification=cls.get_notification_from_dict(error_payload),
            )
            content = render_template(
                "assess/story_edit_content.html",
                **cls.get_item_context(story_id),
            )
            response = make_response(notification_html + content, 400)
            response.headers["HX-Push-Url"] = cls.get_edit_route(**{cls._get_object_key(): story_id})
            return response

        notification_html = cls.render_response_notification(core_response)
        content = render_template(
            "assess/story_edit_content.html",
            **cls.get_item_context(story_id),
        )
        response = make_response(notification_html + content, 200)
        response.headers["HX-Push-Url"] = cls.get_edit_route(**{cls._get_object_key(): story_id})
        return response

    @classmethod
    @auth_required()
    def trigger_bot_action(cls, story_id: str):
        bot_id = request.form.get("bot_id")
        if not bot_id:
            notification = {"message": "Bot identifier is required.", "error": True}
            return render_template("notification/index.html", notification=notification), 400

        api = CoreApi()
        response = api.api_post("/assess/stories/botactions", json_data={"story_id": story_id, "bot_id": bot_id})
        payload = {}
        try:
            payload = response.json()
        except Exception:
            logger.exception("Failed to decode bot action response.")
            payload = {"error": response.text}

        status_code = getattr(response, "status_code", 500)
        DataPersistenceLayer().invalidate_cache_by_object(Story)

        notification_html = render_template(
            "notification/index.html",
            notification=cls.get_notification_from_dict(payload),
        )
        flask_response = make_response(notification_html, status_code)
        flask_response.headers["HX-Trigger"] = json.dumps({"story:reload": True})
        return flask_response

    @classmethod
    @auth_required()
    def news_item_view(cls, news_item_id: str = "0"):
        news_item = DataPersistenceLayer().get_object(NewsItem, news_item_id) if news_item_id != "0" else NewsItem.model_construct(id="0")
        return render_template("assess/news_item_create.html", news_item=news_item), 200

    @classmethod
    @auth_required()
    def create_news_item(cls, news_item_id: str = "0"):
        form_data = parse_formdata(request.form)
        news_item = NewsItem(**form_data)
        api = CoreApi()
        if news_item_id == "0":
            response = api.api_post("/assess/news-items", json_data=news_item.model_dump(mode="json"))
        else:
            response = api.api_put(f"/assess/news-items/{news_item_id}", json_data=news_item.model_dump(mode="json"))

        notification = cls.get_notification_from_response(response)

        notification_html = render_template("notification/index.html", notification=notification)
        response = make_response(notification_html, 200 if getattr(response, "ok", False) else 400)
        response.headers["HX-Trigger"] = json.dumps({"story:reload": True})
        return response

    @classmethod
    @auth_required()
    def patch_story(cls, story_id: str):
        try:
            form_data = parse_formdata(request.form)
            story_update = StoryUpdatePayload(**form_data)
        except ValidationError as exc:
            logger.exception(format_pydantic_errors(exc, StoryUpdatePayload))
            notification = {"message": format_pydantic_errors(exc, StoryUpdatePayload), "error": True}
            notification_html = render_template("notification/index.html", notification=notification)
            return make_response(notification_html, 400)

        response = CoreApi().api_patch(f"/assess/stories/{story_id}", json_data=story_update.model_dump(mode="json"))
        notification_html = cls.get_notification_from_response(response)

        DataPersistenceLayer().invalidate_cache_by_object(Story)

        content = render_template(
            "assess/story.html",
            detail_view=False,
            **cls.get_item_context(story_id),
        )
        response = make_response(notification_html + content, 200)
        return response

    def post(self, *args, **kwargs) -> tuple[str, int] | Response:
        object_id = kwargs.get("story_id")
        if object_id is None:
            abort(405)

        return self.update_from_form(story_id=object_id)

    def put(self, **kwargs) -> tuple[str, int] | Response:
        object_id = kwargs.get("story_id")
        if object_id is None:
            abort(405)

        return self.update_from_form(story_id=object_id)

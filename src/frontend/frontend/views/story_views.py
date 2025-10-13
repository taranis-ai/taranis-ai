from typing import Any
from collections import Counter
from flask_jwt_extended import current_user
from flask import json, render_template, request, url_for, make_response, abort, Response
from pydantic import ValidationError

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
    def get_report_dialog(cls) -> str:
        story_ids = request.form.getlist("story_ids[]")
        reports = DataPersistenceLayer().get_objects(ReportItem)
        return render_template("assess/story_report_dialog.html", story_ids=story_ids, reports=reports)

    @classmethod
    @auth_required()
    def submit_report_dialog(cls) -> str:
        story_ids = request.form.getlist("story_ids[]")
        report_id = request.form.get("report", "")
        logger.debug(f"Submitting report dialog for stories {story_ids} - {report_id}")
        return cls.render_response_notification({"message": "Stories reported successfully", "category": "success"})

    @classmethod
    @auth_required()
    def bulk_action(cls):
        try:
            payload: dict[str, Any] = {request.form.get("action", ""): request.form.get("value")}
            story_action = StoryUpdatePayload(**payload)
            bulk_action = BulkAction(payload=story_action, story_ids=request.form.getlist("story_ids"))
        except ValidationError:
            logger.debug("No story IDs supplied for bulk update. Returning current story list.")
            return cls.list_view()
        response = CoreApi().api_post("/assess/stories/bulk_action", json_data=bulk_action.model_dump(mode="json"))
        if not getattr(response, "ok", False):
            notification = cls.get_notification_from_response(response)
            notification_html = render_template("notification/index.html", notification=notification)
            return make_response(notification_html, 400)

        DataPersistenceLayer().invalidate_cache_by_object(Story)
        return cls.list_view()

    @staticmethod
    def parse_paging_data() -> PagingData:
        """Unmarshal Flask request.args into a PagingData model."""
        args: dict[str, list[str]] = request.args.to_dict(flat=False)

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
    def list_view(cls):
        request_params = request.args.to_dict(flat=False)
        logger.debug(f"Got request params: {request_params}")
        paging_data = cls.parse_paging_data()

        try:
            items = DataPersistenceLayer().get_objects(cls.model, paging_data=paging_data)
            error = None if items else f"No {cls.model_name()} items found"
        except ValidationError as exc:
            logger.exception(format_pydantic_errors(exc, cls.model))
            items, error = None, format_pydantic_errors(exc, cls.model)
        except Exception as exc:
            logger.exception(f"Error retrieving {cls.model_name()} items")
            items, error = None, str(exc)

        return render_template(cls.get_list_template(), **cls.get_view_context(items, error)), 200

    @classmethod
    def render_list(cls) -> tuple[str, int]:
        try:
            items = DataPersistenceLayer().get_objects(cls.model)
            status_code = 200
            error = None
        except ValidationError as exc:
            logger.exception(format_pydantic_errors(exc, cls.model))
            items, error = None, format_pydantic_errors(exc, cls.model)
            status_code = 400
        except Exception as exc:
            logger.exception(f"Error retrieving {cls.model_name()} items")
            items, error = None, str(exc)
            status_code = 500

        return render_template(cls.get_list_template(), **cls.get_view_context(items, error)), status_code

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
            context["sentiment_counts"] = cls._compute_sentiment_counts(story.news_items or [])
        else:
            context["has_rt_id"] = False
            context["story_cyber_status"] = "Not Classified"
            context["cyber_chip_class"] = "badge badge-outline"
            context["sentiment_counts"] = {}

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

    @staticmethod
    def _compute_sentiment_counts(news_items: list[NewsItem]) -> dict[str, int]:
        counts: Counter[str] = Counter()
        for item in news_items:
            attributes = getattr(item, "attributes", []) or []
            for attribute in attributes:
                key = attribute.get("key") if isinstance(attribute, dict) else getattr(attribute, "key", None)
                value = attribute.get("value") if isinstance(attribute, dict) else getattr(attribute, "value", None)
                if key == "sentiment_category" and value:
                    counts[value.lower()] += 1
        return {label: count for label, count in counts.items() if count > 0}

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

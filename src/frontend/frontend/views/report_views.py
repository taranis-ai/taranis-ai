from typing import Any

from flask.typing import ResponseReturnValue
from flask import abort, make_response, render_template, request, url_for
from models.admin import ReportItemType
from models.assess import Story
from models.product import Product
from models.report import ReportItem, ReportItemAttributeGroup
from pydantic import ValidationError

from frontend.auth import auth_required
from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.filters import render_count, render_datetime
from frontend.log import logger
from frontend.utils.form_data_parser import parse_formdata
from frontend.utils.validation_helpers import format_pydantic_errors
from frontend.views.base_view import BaseView


class ReportItemView(BaseView):
    model = ReportItem
    icon = "presentation-chart-bar"
    htmx_list_template = "analyze/report_table.html"
    htmx_update_template = "analyze/report.html"
    edit_template = "analyze/report_view.html"
    default_template = "analyze/index.html"

    base_route = "analyze.analyze"
    edit_route = "analyze.report"

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "Title", "field": "title", "sortable": True, "renderer": None},
            {"title": "Created", "field": "created", "sortable": True, "renderer": render_datetime, "render_args": {"field": "created"}},
            {"title": "Type", "field": "report_item_type", "sortable": False, "renderer": None},
            {
                "title": "Stories",
                "field": "stories",
                "sortable": True,
                "renderer": render_count,
                "render_args": {"field": "stories"},
            },
        ]

    @staticmethod
    def _get_story_attributes(grouped_attributes: list[ReportItemAttributeGroup]):
        story_attributes = []
        used_story_ids = []
        for ag in grouped_attributes:
            for attribute in ag.attributes:
                if not attribute.type or attribute.type != "STORY":
                    continue
                story_attributes.append(attribute)
                used_story_ids.extend(story_id.strip() for story_id in str(attribute.value).split(",") if story_id and story_id.strip())
        return story_attributes, list(dict.fromkeys(used_story_ids))

    @classmethod
    def get_extra_context(cls, base_context: dict[str, Any]) -> dict[str, Any]:
        try:
            report_types = DataPersistenceLayer().get_objects(ReportItemType)
            base_context["report_types"] = report_types
            layout = request.args.get("layout") or request.form.get("layout") or base_context.get("layout", "split")
            report = base_context.get("report")
            base_context["story_attributes"] = []
            base_context["used_story_ids"] = []

            if report := base_context.get("report"):
                if report.grouped_attributes:
                    base_context["story_attributes"], base_context["used_story_ids"] = ReportItemView._get_story_attributes(
                        report.grouped_attributes
                    )

            base_context |= {
                "layout": layout,
                "actions": cls.get_report_actions(),
            }
        except Exception:
            logger.exception("Error getting extra context for ReportItemView")

        return base_context

    @classmethod
    def get_create_context(cls) -> dict[str, Any]:
        context = super().get_create_context()
        report = context.get("report")
        if not report:
            return context
        if title := request.values.get("title"):
            report.title = title
        if report_item_type_id := request.values.get("report_item_type_id"):
            report.report_item_type_id = report_item_type_id
        if story_ids := request.args.getlist("story_ids"):
            report.stories = [s for s in DataPersistenceLayer().get_objects(Story) if s.id in story_ids]
            context["report"] = report

        return context

    @classmethod
    def get_report_actions(cls) -> list[dict[str, Any]]:
        return [
            {
                "label": "Clone Report",
                "icon": "document-duplicate",
                "method": "post",
                "url": url_for("analyze.clone_report", report_id=""),
                "hx_target": f"#{cls.model_name()}-table-container",
                "hx_swap": "outerHTML",
            },
            {"label": "Edit", "class": "btn-primary", "icon": "pencil-square", "url": url_for(cls.edit_route, report_id=""), "type": "link"},
            {
                "label": "Delete",
                "icon": "trash",
                "class": "btn-error",
                "method": "delete",
                "url": url_for(cls.edit_route, report_id=""),
                "hx_target": f"#{cls.model_name()}-table-container",
                "hx_swap": "outerHTML",
                "type": "button",
                "confirm": "Are you sure you want to delete this item?",
            },
        ]

    @staticmethod
    @auth_required()
    def clone_report(report_id: str) -> tuple[str, int] | ResponseReturnValue:
        if not report_id:
            return abort(400, description="No report ID provided for cloning.")
        CoreApi().clone_report(report_id)
        DataPersistenceLayer().invalidate_cache_by_object(ReportItem)
        DataPersistenceLayer().invalidate_cache_by_object(Product)
        return ReportItemView.list_view()

    def post(self, *args, **kwargs) -> tuple[str, int] | ResponseReturnValue:
        return self.update_view(object_id=0)

    def put(self, **kwargs) -> tuple[str, int] | ResponseReturnValue:
        object_id = self._get_object_id(kwargs)
        if object_id is None:
            return abort(405)
        return self.update_view(object_id=object_id)

    @staticmethod
    def _parse_form_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
        return {key: ",".join(id for id in value if id) if isinstance(value, list) else value for key, value in attributes.items()}

    @classmethod
    def process_form_data(cls, object_id: int | str):
        try:
            form_data = parse_formdata(request.form)
            logger.debug(f"Parsed form data: {form_data}")
            form_data.pop("layout", None)
            form_data["attributes"] = cls._parse_form_attributes(form_data.get("attributes", {}))
            return cls.store_form_data(form_data, object_id)
        except ValidationError as exc:
            logger.error(format_pydantic_errors(exc, cls.model))
            return None, format_pydantic_errors(exc, cls.model)
        except Exception as exc:
            logger.error(f"Error storing form data: {str(exc)}")
            return None, str(exc)

    @classmethod
    def update_view(cls, object_id: int | str = 0):
        core_response, error = cls.process_form_data(object_id)
        if not core_response or error:
            return render_template(
                cls.get_update_template(),
                **cls.get_update_context(object_id, error=error, resp_obj=core_response),
            ), 400

        DataPersistenceLayer().invalidate_cache_by_object(Product)

        notification_response = cls.render_response_notification(core_response)
        response = notification_response + render_template(
            cls.get_update_template(),
            **cls.get_update_context(object_id, error=error, resp_obj=core_response),
        )
        flask_response = make_response(response, 200)
        flask_response.headers["HX-Push-Url"] = cls.get_edit_route(**{cls._get_object_key(): core_response.get("id", object_id)})
        return flask_response

    @classmethod
    def delete_view(cls, object_id: str | int) -> tuple[str, int]:
        core_response = DataPersistenceLayer().delete_object(cls.model, object_id)
        if core_response.ok:
            DataPersistenceLayer().invalidate_cache_by_object(Product)

        response = cls.get_notification_from_response(core_response)
        table, table_response = cls.render_list()
        if table_response == 200:
            response += table
        return response, core_response.status_code or table_response

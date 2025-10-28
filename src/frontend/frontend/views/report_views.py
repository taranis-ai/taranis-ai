from typing import Any
from flask import request, abort, Response, url_for
from pydantic import ValidationError

from frontend.log import logger
from models.assess import Story
from models.report import ReportItem, ReportItemAttributeGroup
from models.admin import ReportItemType
from frontend.views.base_view import BaseView
from frontend.data_persistence import DataPersistenceLayer
from frontend.filters import render_datetime, render_count
from frontend.auth import auth_required
from frontend.core_api import CoreApi
from frontend.utils.form_data_parser import parse_formdata
from frontend.utils.validation_helpers import format_pydantic_errors


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
            {"title": "Type", "field": "report_item_type", "sortable": True, "renderer": None},
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
        for ag in grouped_attributes:
            story_attributes.extend(a for a in ag.attributes if a.type and a.type == "STORY")
        return story_attributes

    @classmethod
    def get_extra_context(cls, base_context: dict[str, Any]) -> dict[str, Any]:
        report_types = DataPersistenceLayer().get_objects(ReportItemType)
        base_context["report_types"] = report_types
        layout = request.args.get("layout", base_context.get("layout", "split"))

        base_context |= {
            "layout": layout,
            "actions": cls.get_report_actions(),
        }

        return base_context

    @classmethod
    def get_item_context(cls, object_id: int | str) -> dict[str, Any]:
        context = super().get_item_context(object_id)
        report = context.get("report")
        if not report:
            return context

        if report.grouped_attributes:
            context["story_attributes"] = ReportItemView._get_story_attributes(report.grouped_attributes) or []

        if story_ids := request.args.getlist("story_ids"):
            report.stories.append([s for s in DataPersistenceLayer().get_objects(Story) if s.id in story_ids])
            context["report"] = report
        logger.debug(f"Report item context: {len(context)}")
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
    def clone_report(report_id: str) -> tuple[str, int] | Response:
        if not report_id:
            abort(400, description="No report ID provided for cloning.")
        CoreApi().clone_report(report_id)
        DataPersistenceLayer().invalidate_cache_by_object(ReportItem)
        return ReportItemView.list_view()

    def post(self, *args, **kwargs) -> tuple[str, int] | Response:
        return self.update_view(object_id=0)

    def put(self, **kwargs) -> tuple[str, int] | Response:
        object_id = self._get_object_id(kwargs)
        if object_id is None:
            abort(405)
        return self.update_view(object_id=object_id)

    @staticmethod
    def _parse_form_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
        return {key: ",".join(value) if isinstance(value, list) else value for key, value in attributes.items()}

    @classmethod
    def process_form_data(cls, object_id: int | str):
        try:
            form_data = parse_formdata(request.form)
            form_data["attributes"] = cls._parse_form_attributes(form_data.get("attributes", {}))
            return cls.store_form_data(form_data, object_id)
        except ValidationError as exc:
            logger.error(format_pydantic_errors(exc, cls.model))
            return None, format_pydantic_errors(exc, cls.model)
        except Exception as exc:
            logger.error(f"Error storing form data: {str(exc)}")
            return None, str(exc)

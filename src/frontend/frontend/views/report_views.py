from collections import OrderedDict
from typing import Any
from flask import request, abort, Response, url_for

from frontend.log import logger
from models.report import ReportItem
from models.admin import ReportItemType
from frontend.views.base_view import BaseView
from frontend.data_persistence import DataPersistenceLayer
from frontend.filters import render_datetime, render_count, render_item_type
from frontend.auth import auth_required
from frontend.core_api import CoreApi


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
            {"title": "Type", "field": "type", "sortable": True, "renderer": render_item_type},
            {
                "title": "Stories",
                "field": "stories",
                "sortable": True,
                "renderer": render_count,
                "render_args": {"field": "stories"},
            },
        ]

    @classmethod
    def get_extra_context(cls, base_context: dict[str, Any]) -> dict[str, Any]:
        report_types = DataPersistenceLayer().get_objects(ReportItemType)
        base_context["report_types"] = report_types
        report: ReportItem | None = base_context.get(cls.model_name())  # type: ignore[assignment]
        raw_attributes = report.attributes if report else []
        layout = request.args.get("layout", base_context.get("layout", "split"))
        layout = layout if layout in {"split", "stacked"} else "split"

        base_context |= {
            "layout": layout,
            "grouped_attributes": cls._group_attributes(raw_attributes),
            "used_story_ids": cls._collect_story_attribute_ids(raw_attributes),
            "actions": cls.get_report_actions(),
        }

        return base_context

    @classmethod
    def get_item_context(cls, object_id: int | str) -> dict[str, Any]:
        context = super().get_item_context(object_id)
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
    def _group_attributes(attributes: list | dict[str, str]) -> list[dict[str, Any]]:
        grouped: OrderedDict[str | None, list[Any]] = OrderedDict()

        for attribute in attributes:
            group_title = ReportItemView._get_attribute_value(attribute, "group_title")
            grouped.setdefault(group_title, []).append(attribute)

        result: list[dict[str, Any]] = []
        result.extend({"title": title, "attributes": items} for title, items in grouped.items())
        return result

    @staticmethod
    def _collect_story_attribute_ids(attributes: list | dict[str, str]) -> list[str]:
        collected: list[str] = []
        for attribute in attributes:
            attr_type = str(ReportItemView._get_attribute_value(attribute, "type") or "").upper()
            if attr_type != "STORY":
                continue
            value = ReportItemView._get_attribute_value(attribute, "value")
            values: list[str]
            if isinstance(value, (list, tuple)):
                values = [str(item) for item in value if item]
            elif isinstance(value, str):
                values = [item.strip() for item in value.split(",") if item.strip()]
            else:
                values = []
            for story_id in values:
                if story_id not in collected:
                    collected.append(story_id)
        return collected

    @staticmethod
    @auth_required()
    def clone_report(report_id: str) -> tuple[str, int] | Response:
        if not report_id:
            abort(400, description="No report ID provided for cloning.")
        CoreApi().clone_report(report_id)
        DataPersistenceLayer().invalidate_cache_by_object(ReportItem)
        return ReportItemView.list_view()

    @staticmethod
    def _get_attribute_value(attribute: Any, key: str) -> Any:
        if hasattr(attribute, key):
            return getattr(attribute, key)
        return attribute.get(key) if isinstance(attribute, dict) else None

    def post(self, *args, **kwargs) -> tuple[str, int] | Response:
        return self.update_view(object_id=0)

    def put(self, **kwargs) -> tuple[str, int] | Response:
        object_id = self._get_object_id(kwargs)
        if object_id is None:
            abort(405)
        return self.update_view(object_id=object_id)

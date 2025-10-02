from __future__ import annotations

from collections import OrderedDict
from typing import Any, Iterable

from flask import request

from frontend.log import logger

from models.report import ReportItem
from models.admin import ReportItemType
from frontend.views.base_view import BaseView
from frontend.data_persistence import DataPersistenceLayer
from frontend.filters import render_datetime, render_count, render_item_type


class ReportItemView(BaseView):
    model = ReportItem
    icon = "presentation-chart-bar"
    htmx_list_template = "analyze/report_table.html"
    htmx_update_template = "analyze/report.html"
    edit_template = "analyze/report_view.html"
    default_template = "analyze/index.html"

    base_route = "analyze.analyze"
    edit_route = "analyze.report"
    _read_only = False
    _show_sidebar = False

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
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
        report_types = DataPersistenceLayer().get_objects(ReportItemType)
        base_context["report_types"] = report_types
        return cls._augment_context(base_context)

    @classmethod
    def get_item_context(cls, object_id: int | str) -> dict[str, Any]:
        context = super().get_item_context(object_id)
        logger.debug(f"Report item context: {context}")
        return context

    @classmethod
    def store_form_data(cls, processed_data: dict[str, Any], object_id: int | str = 0):
        logger.debug(f"Storing report form data: {processed_data} for id {object_id}")
        return super().store_form_data(processed_data, object_id)

    @classmethod
    def _augment_context(cls, context: dict[str, Any]) -> dict[str, Any]:
        report: ReportItem | None = context.get(cls.model_name())  # type: ignore[assignment]
        raw_attributes = list(getattr(report, "attributes", []) or []) if report else []
        stories = list(getattr(report, "stories", []) or []) if report else []

        layout = request.args.get("layout", context.get("layout", "split"))
        layout = layout if layout in {"split", "stacked"} else "split"

        context.update(
            {
                "layout": layout,
                "grouped_attributes": cls._group_attributes(raw_attributes),
                "stories": stories,
                "used_story_ids": cls._collect_story_attribute_ids(raw_attributes),
            }
        )

        return context

    @staticmethod
    def _group_attributes(attributes: Iterable[Any]) -> list[dict[str, Any]]:
        grouped: OrderedDict[str | None, list[Any]] = OrderedDict()

        for attribute in attributes:
            group_title = ReportItemView._get_attribute_value(attribute, "group_title")
            grouped.setdefault(group_title, []).append(attribute)

        result: list[dict[str, Any]] = []
        result.extend({"title": title, "attributes": items} for title, items in grouped.items())
        return result

    @staticmethod
    def _collect_story_attribute_ids(attributes: Iterable[Any]) -> list[str]:
        collected: list[str] = []
        for attribute in attributes:
            attr_type = str(ReportItemView._get_attribute_value(attribute, "type") or "").upper()
            if attr_type != "STORY":
                continue
            value = ReportItemView._get_attribute_value(attribute, "value")
            values: Iterable[str]
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
    def _get_attribute_value(attribute: Any, key: str) -> Any:
        if hasattr(attribute, key):
            return getattr(attribute, key)
        return attribute.get(key) if isinstance(attribute, dict) else None

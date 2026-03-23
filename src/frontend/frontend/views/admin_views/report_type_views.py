from typing import Any

from flask import render_template
from models.admin import Attribute, ReportItemAttribute, ReportItemAttributeGroup, ReportItemType

from frontend.data_persistence import DataPersistenceLayer
from frontend.views.admin_views.admin_mixin import AdminMixin
from frontend.views.base_view import BaseView


class ReportItemTypeView(AdminMixin, BaseView):
    model = ReportItemType
    icon = "presentation-chart-bar"
    _index = 120

    @classmethod
    def _normalize_form_data(cls, form_data: dict[str, Any]) -> dict[str, Any]:
        attribute_groups = form_data.get("attribute_groups", {})
        if isinstance(attribute_groups, dict):
            attribute_groups = list(attribute_groups.values())
        else:
            attribute_groups = list(attribute_groups or [])

        for group in attribute_groups:
            if items := group.get("attribute_group_items"):
                group["attribute_group_items"] = list(items.values()) if isinstance(items, dict) else list(items)
            else:
                group["attribute_group_items"] = []

        form_data["attribute_groups"] = attribute_groups
        return form_data

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "Title", "field": "title", "sortable": True, "renderer": None},
            {"title": "Description", "field": "description", "sortable": True, "renderer": None},
        ]

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
        dpl = DataPersistenceLayer()
        base_context["attribute_types"] = dpl.get_objects(Attribute)
        return base_context

    @classmethod
    def get_report_item_type_groups_view(cls, group_index: int = 0):
        return render_template(
            "report_item_type/attribute_group.html", group=ReportItemAttributeGroup(index=group_index), **cls.get_extra_context({})
        )

    @classmethod
    def get_report_item_type_group_items_view(cls, group_index: int, attribute_index: int = 0):
        return render_template(
            "report_item_type/attribute_item.html",
            attribute=ReportItemAttribute(index=attribute_index),
            group_index=group_index,
            **cls.get_extra_context({}),
        )

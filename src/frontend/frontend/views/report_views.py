from typing import Any
from flask import render_template, request

from frontend.views.base_view import BaseView
from models.admin import ReportItemType, Attribute, ReportItemAttributeGroup, ReportItemAttribute
from frontend.data_persistence import DataPersistenceLayer
from frontend.utils.form_data_parser import parse_formdata


class ReportItemTypeView(BaseView):
    model = ReportItemType
    icon = "presentation-chart-bar"
    _index = 120

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

    @classmethod
    def process_form_data(cls, object_id: int | str):
        form_data = parse_formdata(request.form)
        attribute_groups = list(form_data.get("attribute_groups", {}).values())
        for group in attribute_groups:
            if items := group.get("attribute_group_items"):
                group["attribute_group_items"] = list(items.values())

        form_data["attribute_groups"] = attribute_groups
        return cls.store_form_data(form_data, object_id)

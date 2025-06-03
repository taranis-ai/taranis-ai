from typing import Any
from flask import render_template, request

from frontend.views.base_view import BaseView
from models.admin import ReportItemType, Attribute, ReportItemAttributeGroup
from frontend.data_persistence import DataPersistenceLayer
from frontend.router_helpers import parse_formdata
from frontend.log import logger


class ReportItemTypeView(BaseView):
    model = ReportItemType
    icon = "presentation-chart-bar"
    _index = 120

    form_fields = {"title": {}, "description": {}}

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "ID", "field": "id", "sortable": False, "renderer": None},
            {"title": "Title", "field": "title", "sortable": True, "renderer": None},
            {"title": "Description", "field": "description", "sortable": True, "renderer": None},
        ]

    @classmethod
    def get_extra_context(cls, object_id: int | str):
        dpl = DataPersistenceLayer()
        return {"attributes": [p.model_dump() for p in dpl.get_objects(Attribute)]}

    @classmethod
    def get_report_item_type_groups_view(cls):
        return render_template("report_item_type/attribute_group.html", group=ReportItemAttributeGroup())

    @classmethod
    def process_form_data(cls, object_id: int | str):
        logger.debug(f"Form data: {request.form}")
        form_data = parse_formdata(request.form)
        logger.debug(f"Parsed Formdata: {form_data}")
        attribute_groups = form_data.get("attribute_groups", {}).values()
        logger.debug(f"Attribute Groups: {attribute_groups} - Type: {type(attribute_groups)}")
        form_data["attribute_groups"] = attribute_groups
        logger.debug(f"Processed Formdata: {form_data}")
        return cls.store_form_data(form_data, object_id)

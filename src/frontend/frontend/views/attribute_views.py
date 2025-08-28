from typing import Any
from flask import request

from frontend.views.base_view import BaseView
from models.admin import Attribute
from models.types import AttributeType
from frontend.data_persistence import DataPersistenceLayer
from frontend.utils.form_data_parser import parse_formdata
from frontend.filters import render_item_type


class AttributeView(BaseView):
    model = Attribute
    icon = "document-arrow-up"
    _index = 130

    attribute_types = {
        member.name.lower(): {"id": member.name.lower(), "name": " ".join(part.capitalize() for part in member.name.split("_"))}
        for member in AttributeType
    }

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
        base_context["attribute_types"] = cls.attribute_types.values()
        return base_context

    @classmethod
    def process_form_data(cls, object_id: int | str):
        try:
            form_data = parse_formdata(request.form)
            form_data["attribute_enums"] = [enum for enum in form_data["attribute_enums"] if enum]
            obj = cls.model(**form_data)
            dpl = DataPersistenceLayer()
            result = dpl.store_object(obj) if object_id == 0 else dpl.update_object(obj, object_id)
            return (result.json(), None) if result.ok else (None, result.json().get("error"))
        except Exception as exc:
            return None, str(exc)

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "Name", "field": "name", "sortable": True, "renderer": None},
            {"title": "Description", "field": "description", "sortable": True, "renderer": None},
            {"title": "Type", "field": "type", "sortable": True, "renderer": render_item_type},
        ]

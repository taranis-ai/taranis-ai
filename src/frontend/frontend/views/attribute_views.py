from typing import Any
from flask import request

from frontend.views.base_view import BaseView
from models.admin import Attribute
from models.types import AttributeType
from frontend.data_persistence import DataPersistenceLayer
from frontend.router_helpers import parse_formdata


class AttributeView(BaseView):
    model = Attribute
    icon = "document-arrow-up"
    _index = 130

    attribute_types = {
        member.name.lower(): {"id": member.name.upper(), "name": " ".join(part.capitalize() for part in member.name.split("_"))}
        for member in AttributeType
    }

    @classmethod
    def get_extra_context(cls, object_id: int | str) -> dict[str, Any]:
        return {"attribute_types": cls.attribute_types.values()}

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

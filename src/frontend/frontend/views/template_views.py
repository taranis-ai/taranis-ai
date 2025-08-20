from base64 import b64encode
from typing import Any
from flask import request, render_template, Response
from base64 import b64decode, b64encode
from flask import request

from frontend.views.base_view import BaseView
from frontend.log import logger
from models.admin import Template
from frontend.data_persistence import DataPersistenceLayer
from frontend.utils.form_data_parser import parse_formdata


class TemplateView(BaseView):
    model = Template
    icon = "document-text"
    _index = 160
    htmx_list_template: str = "template/template_data_table.html"

    @classmethod
    def model_plural_name(cls) -> str:
        return "template_data"

    @classmethod
    def get_columns(cls):
        from frontend.filters import render_item_validation_status
        return [
            {"title": "Template Name", "field": "id", "sortable": True, "renderer": None},
            {"title": "Validation Status", "field": "validation_status", "sortable": False, "renderer": render_item_validation_status}
        ]


    @classmethod
    def _get_object_key(cls) -> str:
        return f"{cls.model_name().lower()}"

    @classmethod
    def get_update_context(
        cls,
        object_id: int | str,
        error: str | None = None,
        form_error: str | None = None,
        resp_obj=None,
    ) -> dict[str, Any]:
        context = super().get_update_context(
            object_id=object_id,
            error=error,
            form_error=form_error,
            resp_obj=resp_obj,
        )

        dpl = DataPersistenceLayer()
        template = dpl.get_object(cls.model, object_id) or cls.model.model_construct(id=str(object_id), content='')
        validation_status = getattr(template, 'validation_status', None) or {}
        context[cls.model_name()] = template
        context["validation_status"] = validation_status
        return context

    @classmethod
    def process_form_data(cls, object_id: str | int):
        try:
            form_data = parse_formdata(request.form)
            obj = Template(**form_data)
            if obj.content:
                obj.content = b64encode(obj.content.encode("utf-8")).decode("utf-8")
            dpl = DataPersistenceLayer()
            result = dpl.store_object(obj) if object_id == 0 else dpl.update_object(obj, object_id)
            return (result.json(), None) if result.ok else (None, result.json().get("error"))
        except Exception as exc:
            logger.error(f"Error storing form data: {str(exc)}")
            return None, str(exc)

from base64 import b64encode, b64decode
from typing import Any
from flask import request

from frontend.views.base_view import BaseView
from frontend.log import logger
from models.admin import Template
from frontend.data_persistence import DataPersistenceLayer
from frontend.utils.form_data_parser import parse_formdata
from frontend.views.admin_views.admin_mixin import AdminMixin


class TemplateView(AdminMixin, BaseView):
    model = Template
    icon = "document-text"
    _index = 160
    htmx_list_template = "template/template_data_table.html"

    @classmethod
    def model_plural_name(cls) -> str:
        return "template_data"

    @classmethod
    def get_columns(cls):
        from frontend.filters import render_item_validation_status

        return [
            {"title": "Template Name", "field": "id", "sortable": True, "renderer": None},
            {"title": "Validation Status", "field": "validation_status", "sortable": False, "renderer": render_item_validation_status},
        ]

    @classmethod
    def _get_object_key(cls) -> str:
        return "template"

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
        template: Template = base_context.get(cls._get_object_key())  # type: ignore
        if not isinstance(template, Template):
            return base_context

        try:
            template.content = b64decode(template.content or "").decode("utf-8")
        except Exception:
            logger.exception()
            logger.warning(f"Failed to decode template content for {template}")
            template.content = template.content

        base_context[cls.model_name()] = template
        validation_status = getattr(template, "validation_status", None) or {}
        base_context["validation_status"] = validation_status
        return base_context

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

from typing import Any
from base64 import b64decode, b64encode
from flask import request

from frontend.views.base_view import BaseView
from frontend.log import logger
from models.admin import Template
from frontend.data_persistence import DataPersistenceLayer
from frontend.router_helpers import parse_formdata


class TemplateView(BaseView):
    model = Template
    icon = "document-text"
    _index = 160

    @classmethod
    def model_plural_name(cls) -> str:
        return "template_data"

    @classmethod
    def get_columns(cls):
        return [{"title": "name", "field": "id", "sortable": True, "renderer": None}]

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
        raw_model = dpl.get_object(cls.model, object_id) or cls.model()
        template = Template(**raw_model.model_dump())

        try:
            template.content = b64decode(template.content or "").decode("utf-8")
        except Exception:
            logger.exception()
            logger.warning(f"Failed to decode template content for {template}")
            template.content = template.content

        context[cls.model_name()] = template
        return context

    @classmethod
    def process_form_data(cls, object_id: int | str):
        try:
            obj = Template(**parse_formdata(request.form))
            if obj.content:
                obj.content = b64encode(obj.content.encode("utf-8")).decode("utf-8")
            dpl = DataPersistenceLayer()
            result = dpl.store_object(obj) if object_id == 0 else dpl.update_object(obj, object_id)
            return (result.json(), None) if result.ok else (None, result.json().get("error"))
        except Exception as exc:
            return None, str(exc)

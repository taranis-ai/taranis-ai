from flask import render_template, request, Response
from typing import Type

from frontend.data_persistence import DataPersistenceLayer
from frontend.router_helpers import is_htmx_request, parse_formdata
from frontend.models import TaranisBaseModel


class BaseView:
    model: Type[TaranisBaseModel]
    id_key = ""
    htmx_template = ""
    default_template = ""

    @classmethod
    def process_form_data(cls, object_id: int):
        """Generic form data processor for creating/updating an object."""
        try:
            obj = cls.model(**parse_formdata(request.form))
            dpl = DataPersistenceLayer()
            result = dpl.store_object(obj) if object_id == 0 else dpl.update_object(obj, object_id)
            return (obj, None) if result.ok else (None, result.json().get("error"))
        except Exception as exc:
            return None, str(exc)

    @classmethod
    def select_template(cls):
        """Selects the appropriate template based on the request type."""
        return cls.htmx_template if is_htmx_request() else cls.default_template

    @classmethod
    def get_context(
        cls, object_id: int, error: str | None = None, form_error: str | None = None, data_obj=None, extra_context: dict | None = None
    ):
        """Builds the context dictionary, merging in any extra context."""
        dpl = DataPersistenceLayer()
        context = {f"{cls.id_key}_id": object_id, "error": error, "form_error": form_error}
        if extra_context:
            context |= extra_context
        if object_id != 0:
            context[cls.id_key] = data_obj or dpl.get_object(cls.model, object_id)
        return context

    @classmethod
    def update_view(cls, object_id: int = 0, extra_context: dict | None = None):
        """Generic update view handling form submission."""
        data_obj, error = cls.process_form_data(object_id)
        if data_obj:
            return Response(status=200, headers={"HX-Refresh": "true"})
        template = cls.select_template()
        context = cls.get_context(object_id, error=error, data_obj=data_obj, extra_context=extra_context)
        return render_template(template, **context)

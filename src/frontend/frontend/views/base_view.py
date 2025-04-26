from flask import render_template, request, Response, url_for
from typing import Type, Any

from frontend.data_persistence import DataPersistenceLayer
from frontend.router_helpers import is_htmx_request, parse_formdata, convert_query_params
from frontend.models import TaranisBaseModel, PagingData
from frontend.log import logger


class BaseView:
    model: Type[TaranisBaseModel]
    htmx_update_template = ""
    htmx_list_template = ""
    default_template = ""
    base_route = ""
    edit_route = ""
    _registry = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseView._registry[cls.model_name().capitalize()] = cls

    @classmethod
    def model_name(cls) -> str:
        """Returns the name of the model class."""
        return cls.model._model_name

    @classmethod
    def model_plural_name(cls) -> str:
        """Returns the plural name of the model class."""
        return f"{cls.model._model_name}s"

    @classmethod
    def process_form_data(cls, object_id: int):
        """Generic form data processor for creating/updating an object."""
        try:
            obj = cls.model(**parse_formdata(request.form))
            result = DataPersistenceLayer().store_object(obj) if object_id == 0 else DataPersistenceLayer().update_object(obj, object_id)
            return (result.json(), None) if result.ok else (None, result.json().get("error"))
        except Exception as exc:
            return None, str(exc)

    @classmethod
    def get_list_template(
        cls,
    ):
        """Selects the appropriate template based on the request type."""
        return cls.htmx_list_template if is_htmx_request() else cls.default_template

    @classmethod
    def get_update_template(cls):
        """Selects the appropriate template for the update view."""
        return cls.htmx_update_template if is_htmx_request() else cls.default_template

    @classmethod
    def get_extra_context(cls, object_id: int):
        """Returns any extra context needed for rendering the template."""
        return {}

    @classmethod
    def edit_view(cls, object_id: int = 0):
        template = cls.get_update_template()
        context = cls.get_update_context(object_id)
        return render_template(template, **context)

    @classmethod
    def get_update_context(cls, object_id: int, error: str | None = None, form_error: str | None = None, resp_obj=None):
        """Builds the context dictionary, merging in any extra context."""
        dpl = DataPersistenceLayer()
        if object_id == 0:
            form_action = f"hx-post={url_for(cls.base_route)}"
        else:
            route_args: dict[str, Any] = {f"{cls.model_name()}_id": object_id}
            form_action = f"hx-put={url_for(cls.edit_route, **route_args)}"

        context = {
            f"{cls.model_name()}_id": object_id,
            "error": error,
            "form_error": form_error,
            "form_action": form_action,
            "model_name": cls.model_name(),
        }

        context |= cls.get_extra_context(object_id)
        if resp_obj:
            context[cls.model_name()] = resp_obj.get(cls.model_name())
            if message := resp_obj.get("message"):
                context["message"] = message
        if object_id != 0 and not resp_obj:
            context[cls.model_name()] = dpl.get_object(cls.model, object_id)
        if object_id == 0 and not resp_obj:
            context[cls.model_name()] = cls.model()
        return context

    @classmethod
    def update_view(cls, object_id: int = 0):
        """Generic update view handling form submission."""
        resp_obj, error = cls.process_form_data(object_id)
        if error:
            logger.error(f"Error processing form data: {error}")
        if resp_obj and not error:
            return Response(status=200, headers={"HX-Redirect": url_for(cls.base_route)})
        template = cls.get_update_template()
        context = cls.get_update_context(object_id, error=error, resp_obj=resp_obj)
        return render_template(template, **context)

    @classmethod
    def list_view(cls):
        try:
            params = convert_query_params(request.args, PagingData)
            page = PagingData(**params)
            items = DataPersistenceLayer().get_objects(cls.model, page)
            error = None
        except Exception as exc:
            items = None
            error = str(exc)

        template = cls.get_list_template()
        return render_template(template, **{f"{cls.model_plural_name()}": items, "error": error})

    @classmethod
    def static_view(cls):
        try:
            items = DataPersistenceLayer().get_objects(cls.model)
            error = None
        except Exception as exc:
            items = None
            error = str(exc)

        if not items:
            logger.error(f"Error retrieving {cls.model_name()} items: {error}")
            return render_template("errors/404.html", error="No Dashboard items found")
        template = cls.get_list_template()
        return render_template(template, **{f"{cls.model_plural_name()}": items, "error": error})

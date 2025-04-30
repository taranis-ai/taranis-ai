from flask import render_template, request, Response, url_for
from typing import Type, Any
from models.admin import TaranisBaseModel
from pydantic import ValidationError

from frontend.data_persistence import DataPersistenceLayer
from frontend.router_helpers import is_htmx_request, parse_formdata, convert_query_params
from frontend.cache_models import PagingData
from frontend.log import logger


class BaseView:
    model: Type[TaranisBaseModel]
    htmx_update_template: str = ""
    htmx_list_template: str = ""
    default_template: str = ""
    base_route: str = ""
    edit_route: str = ""
    _registry = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseView._registry[cls.pretty_name()] = cls

    @classmethod
    def model_name(cls) -> str:
        return cls.model._model_name

    @classmethod
    def model_plural_name(cls) -> str:
        return f"{cls.model._model_name}s"

    @classmethod
    def pretty_name(cls) -> str:
        return cls.model._pretty_name or cls.model_name().capitalize()

    @classmethod
    def get_htmx_list_template(cls) -> str:
        return cls.htmx_list_template or f"{cls.model_name().lower()}/{cls.model_plural_name().lower()}_table.html"

    @classmethod
    def get_htmx_update_template(cls) -> str:
        return cls.htmx_update_template or f"{cls.model_name().lower()}/{cls.model_name().lower()}_form.html"

    @classmethod
    def get_default_template(cls) -> str:
        return cls.default_template or f"{cls.model_name().lower()}/index.html"

    @classmethod
    def get_base_route(cls, **kwargs) -> str:
        route = cls.base_route or f"admin.{cls.model_plural_name().lower()}"
        return url_for(route, **kwargs)

    @classmethod
    def get_edit_route(cls, **kwargs) -> str:
        route = cls.edit_route or f"admin.edit_{cls.model_name().lower()}"
        return url_for(route, **kwargs)

    @classmethod
    def process_form_data(cls, object_id: int):
        try:
            obj = cls.model(**parse_formdata(request.form))
            result = DataPersistenceLayer().store_object(obj) if object_id == 0 else DataPersistenceLayer().update_object(obj, object_id)
            return (result.json(), None) if result.ok else (None, result.json().get("error"))
        except Exception as exc:
            return None, str(exc)

    @classmethod
    def get_list_template(cls):
        return cls.get_htmx_list_template() if is_htmx_request() else cls.get_default_template()

    @classmethod
    def get_update_template(cls):
        return cls.get_htmx_update_template() if is_htmx_request() else cls.get_default_template()

    @classmethod
    def get_extra_context(cls, object_id: int):
        return {}

    @classmethod
    def edit_view(cls, object_id: int = 0):
        template = cls.get_update_template()
        context = cls.get_update_context(object_id)
        logger.debug(f"Rendering template: {template} with context: {context}")
        return render_template(template, **context)

    @classmethod
    def get_update_context(cls, object_id: int, error: str | None = None, form_error: str | None = None, resp_obj=None):
        dpl = DataPersistenceLayer()
        if object_id == 0:
            form_action = f"hx-post={cls.get_base_route()}"
        else:
            route_args: dict[str, Any] = {f"{cls.model_name()}_id": object_id}
            form_action = f"hx-put={cls.get_edit_route(**route_args)}"

        context = {
            f"{cls.model_name()}_id": object_id,
            "error": error,
            "form_error": form_error,
            "form_action": form_action,
            "model_name": cls.model_name(),
            "name": cls.pretty_name(),
        }

        if resp_obj:
            context[cls.model_name()] = resp_obj.get(cls.model_name())
            if message := resp_obj.get("message"):
                context["message"] = message
        else:
            context[cls.model_name()] = cls.model().model_dump(mode="json") if object_id == 0 else dpl.get_object(cls.model, object_id)
        context |= cls.get_extra_context(object_id)
        return context

    @classmethod
    def get_view_context(cls, objects: list[TaranisBaseModel] | None = None, error: str | None = None):
        context = {
            f"{cls.model_plural_name()}": objects,
            "error": error,
            "name": cls.pretty_name(),
            "model_name": cls.model_name(),
        }
        context |= cls.get_extra_context(0)
        return context

    @classmethod
    def update_view(cls, object_id: int = 0):
        resp_obj, error = cls.process_form_data(object_id)
        if error:
            logger.error(f"Error processing form data: {error}")
        if resp_obj and not error:
            return Response(status=200, headers={"HX-Redirect": cls.get_base_route()})
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
        except ValidationError as exc:
            logger.exception(f"Error validating {cls.model_name()}")
            items = None
            error = exc.errors()[0]["msg"]
        except Exception as exc:
            items = None
            error = str(exc)

        template = cls.get_list_template()
        context = cls.get_view_context(items, error)
        logger.debug(f"Rendering template: {template} with context: {context}")
        return render_template(template, **context)

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
            return render_template("errors/404.html", error=f"No {cls.model_name()} items found")
        template = cls.get_list_template()
        return render_template(template, **{f"{cls.model_plural_name()}": items, "error": error})

    @classmethod
    def delete_view(cls, object_id):
        result = DataPersistenceLayer().delete_object(cls.model, object_id)
        return Response(status=result.status_code, headers={"HX-Refresh": "true"}) if result else "error"

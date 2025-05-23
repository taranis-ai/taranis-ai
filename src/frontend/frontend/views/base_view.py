from flask import render_template, request, Response, url_for, current_app, abort
from jinja2 import TemplateNotFound
from typing import Type, Any
from pydantic import ValidationError
from flask.views import MethodView

from models.admin import TaranisBaseModel
from frontend.data_persistence import DataPersistenceLayer
from frontend.router_helpers import is_htmx_request, parse_formdata, convert_query_params
from frontend.cache_models import PagingData
from frontend.log import logger
from frontend.auth import auth_required


class BaseView(MethodView):
    model: Type[TaranisBaseModel]

    htmx_update_template: str = ""
    htmx_list_template: str = ""
    default_template: str = ""
    edit_template: str = ""
    base_route: str = ""
    edit_route: str = ""
    icon: str = "wrench"
    _index: float | int = float("inf")

    _registry: dict[str, Any] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseView._registry[cls.pretty_name()] = cls

    @classmethod
    def _common_context(cls, error: str | None = None, object_id: int | str = 0) -> dict[str, Any]:
        return {
            "error": error,
            "name": cls.pretty_name(),
            "templates": cls.get_template_urls(),
            "columns": cls.get_columns(),
            "routes": {
                "base_route": cls.get_base_route(),
                "edit_route": cls.get_edit_route(**{cls._get_object_key(): object_id}),
            },
            "model_name": cls.model_name(),
            "model_plural_name": cls.model_plural_name(),
            cls._get_object_key(): object_id,
        }

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
    def _fallback_template(cls, path: str, fallback_suffix: str) -> str:
        """
        Return `path` if it exists in the Jinja loader; otherwise fallback to `default/{model_name}{fallback_suffix}`.
        """
        try:
            current_app.jinja_env.get_template(path)
            return path
        except TemplateNotFound:
            base_fallback = request.endpoint.split(".")[0] if request.endpoint else cls.model_name().lower()
            return f"default/{base_fallback}{fallback_suffix}"

    @classmethod
    def get_htmx_list_template(cls) -> str:
        path = cls.htmx_list_template or (f"{cls.model_name().lower()}/{cls.model_plural_name().lower()}_table.html")
        return cls._fallback_template(path, "_table.html")

    @classmethod
    def get_htmx_update_template(cls) -> str:
        path = cls.htmx_update_template or (f"{cls.model_name().lower()}/{cls.model_name().lower()}_form.html")
        return cls._fallback_template(path, "_form.html")

    @classmethod
    def get_edit_template(cls) -> str:
        path = cls.edit_template or (f"{cls.model_name().lower()}/{cls.model_name().lower()}_edit.html")
        return cls._fallback_template(path, "_edit.html")

    @classmethod
    def get_default_template(cls) -> str:
        path = cls.default_template or (f"{cls.model_name().lower()}/index.html")
        return cls._fallback_template(path, "_index.html")

    @classmethod
    def get_base_route(cls, **kwargs) -> str:
        route = cls.base_route or f"admin.{cls.model_plural_name().lower()}"
        return url_for(route, **kwargs)

    @classmethod
    def get_edit_route(cls, **kwargs) -> str:
        route = cls.edit_route or f"admin.edit_{cls.model_name().lower()}"
        return url_for(route, **kwargs)

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "ID", "field": "id", "sortable": False, "renderer": None},
            {"title": "Name", "field": "name", "sortable": True, "renderer": None},
            {"title": "Description", "field": "description", "sortable": True, "renderer": None},
        ]

    @classmethod
    def process_form_data(cls, object_id: int | str):
        try:
            obj = cls.model(**parse_formdata(request.form))
            dpl = DataPersistenceLayer()
            result = dpl.store_object(obj) if object_id == 0 else dpl.update_object(obj, object_id)
            return (result.json(), None) if result.ok else (None, result.json().get("error"))
        except Exception as exc:
            return None, str(exc)

    @classmethod
    def get_list_template(cls) -> str:
        return cls.get_htmx_list_template() if is_htmx_request() else cls.get_default_template()

    @classmethod
    def get_update_template(cls) -> str:
        return cls.get_htmx_update_template() if is_htmx_request() else cls.get_edit_template()

    @classmethod
    def get_extra_context(cls, object_id: int | str) -> dict[str, Any]:
        return {}

    @classmethod
    def get_template_urls(cls) -> dict[str, str]:
        return {
            "htmx_update_template": cls.get_htmx_update_template(),
            "htmx_list_template": cls.get_htmx_list_template(),
            "update_template": cls.get_update_template(),
            "list_template": cls.get_list_template(),
            "default_template": cls.get_default_template(),
        }

    @classmethod
    def edit_view(cls, object_id: int | str = 0):
        return render_template(cls.get_update_template(), **cls.get_update_context(object_id))

    @classmethod
    def get_update_context(
        cls,
        object_id: int | str,
        error: str | None = None,
        form_error: str | None = None,
        resp_obj=None,
    ) -> dict[str, Any]:
        dpl = DataPersistenceLayer()
        if str(object_id) == "0":
            form_action = f"hx-post={cls.get_base_route()}"
            submit = f"Create {cls.pretty_name()}"
        else:
            key = cls._get_object_key()
            form_action = f"hx-put={cls.get_edit_route(**{key: object_id})}"
            submit = f"Update {cls.pretty_name()}"

        context = cls._common_context(error, object_id)
        context.update(
            {
                "form_error": form_error,
                "form_action": form_action,
                "submit_text": submit,
            }
        )

        if resp_obj:
            context[cls.model_name()] = resp_obj.get(cls.model_name())
            if msg := resp_obj.get("message"):
                context["message"] = msg
        else:
            context[cls.model_name()] = cls.model.model_construct() if str(object_id) == "0" else dpl.get_object(cls.model, object_id)

        context |= cls.get_extra_context(object_id)
        return context

    @classmethod
    def get_view_context(
        cls,
        objects: list[TaranisBaseModel] | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        context = cls._common_context(error)
        if objects:
            context[f"{cls.model_plural_name()}"] = objects
        context |= cls.get_extra_context(0)
        return context

    @classmethod
    def update_view(cls, object_id: int | str = 0):
        resp_obj, error = cls.process_form_data(object_id)
        if error:
            logger.error(f"Error processing form data: {error}")
        if resp_obj and not error:
            return Response(status=200, headers={"HX-Redirect": cls.get_base_route()})

        return render_template(
            cls.get_update_template(),
            **cls.get_update_context(object_id, error=error, resp_obj=resp_obj),
        )

    @classmethod
    def list_view(cls):
        try:
            params = convert_query_params(request.args, PagingData)
            page = PagingData(**params)
            items = DataPersistenceLayer().get_objects(cls.model, page)
            error = None if items else f"No {cls.model_name()} items found"
        except ValidationError as exc:
            logger.exception(f"Error validating {cls.model_name()}")
            items, error = None, exc.errors()[0]["msg"]
        except Exception as exc:
            logger.exception(f"Error retrieving {cls.model_name()} items")
            items, error = None, str(exc)

        if error and is_htmx_request():
            logger.error(f"Error retrieving {cls.model_name()} items: {error}")
            return render_template("partials/error.html", error=error), 400

        return render_template(cls.get_list_template(), **cls.get_view_context(items, error))

    @classmethod
    def static_view(cls):
        try:
            items = DataPersistenceLayer().get_objects(cls.model)
            error = None
        except Exception as exc:
            logger.exception(f"Error retrieving {cls.model_name()} items")
            items, error = None, str(exc)

        if not items:
            logger.error(f"Error retrieving {cls.model_name()} items: {error}")
            return render_template("errors/404.html", error=f"No {cls.model_name()} items found")

        return render_template(cls.get_list_template(), **{f"{cls.model_plural_name()}": items, "error": error})

    @classmethod
    def delete_view(cls, object_id: str | int):
        result = DataPersistenceLayer().delete_object(cls.model, object_id)
        if result:
            return Response(status=result.status_code, headers={"HX-Refresh": "true"})
        return "error"

    @classmethod
    def delete_multiple_view(cls, object_ids: list[str]):
        results = []
        results.extend(DataPersistenceLayer().delete_object(cls.model, object_id) for object_id in object_ids)
        if any(r.ok for r in results):
            return Response(status=200, headers={"HX-Refresh": "true"})
        return Response(status=400, headers={"HX-Refresh": "true"})

    @classmethod
    def _get_object_key(cls) -> str:
        return f"{cls.model_name().lower()}_id"

    def _get_object_id(self, kwargs: dict) -> int | str | None:
        key = self._get_object_key()
        return kwargs.get(key)

    @auth_required()
    def get(self, **kwargs):
        object_id = self._get_object_id(kwargs)
        if object_id is None:
            return self.list_view()
        return self.edit_view(object_id=object_id)

    @auth_required()
    def post(self):
        return self.update_view(object_id=0)

    @auth_required()
    def put(self, **kwargs):
        object_id = self._get_object_id(kwargs)
        if object_id is None:
            abort(405)
        return self.update_view(object_id=object_id)

    @auth_required()
    def delete(self, **kwargs):
        object_id = self._get_object_id(kwargs)
        if object_id is None:
            ids = request.form.getlist("ids")
            return self.delete_multiple_view(object_ids=ids)
        return self.delete_view(object_id=object_id)

from flask import render_template, request, url_for, current_app, abort
from jinja2 import TemplateNotFound
from typing import ClassVar, Type, Any
from pydantic import ValidationError
from flask.views import MethodView
from requests import Response as RequestsResponse

from models.admin import TaranisBaseModel, WorkerParameter, WorkerParameterValue
from frontend.data_persistence import DataPersistenceLayer
from frontend.utils.router_helpers import is_htmx_request, convert_query_params
from frontend.utils.form_data_parser import parse_formdata
from frontend.cache_models import PagingData, CacheObject
from frontend.log import logger
from frontend.auth import auth_required
from frontend.utils.validation_helpers import format_pydantic_errors


class BaseView(MethodView):
    model: ClassVar[Type[TaranisBaseModel]]

    decorators = [auth_required()]
    htmx_update_template: ClassVar[str] = ""
    htmx_list_template: ClassVar[str] = ""
    default_template: ClassVar[str] = ""
    edit_template: ClassVar[str] = ""
    base_route: ClassVar[str] = ""
    edit_route: ClassVar[str] = ""
    import_route: ClassVar[str] = ""
    icon: ClassVar[str] = "wrench"
    _is_admin: ClassVar[bool] = False
    _show_sidebar: ClassVar[bool] = True
    _index: ClassVar[float | int] = float("inf")
    _read_only: ClassVar[bool] = False

    _registry: ClassVar[dict[str, Any]] = {}

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
            "_is_admin": cls._is_admin,
            "_show_sidebar": cls._show_sidebar,
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
        return url_for(cls.base_route, **kwargs) if cls.base_route else ""

    @classmethod
    def get_edit_route(cls, **kwargs) -> str:
        return url_for(cls.edit_route, **kwargs) if cls.edit_route else ""

    @classmethod
    def get_import_route(cls, **kwargs) -> str:
        return url_for(cls.import_route, **kwargs) if cls.import_route else ""

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "Name", "field": "name", "sortable": True, "renderer": None},
            {"title": "Description", "field": "description", "sortable": True, "renderer": None},
            {"title": "ID", "field": "id", "sortable": False, "renderer": None},
        ]

    @classmethod
    def process_form_data(cls, object_id: int | str):
        try:
            form_data = parse_formdata(request.form)
            return cls.store_form_data(form_data, object_id)
        except ValidationError as exc:
            logger.error(format_pydantic_errors(exc, cls.model))
            return None, format_pydantic_errors(exc, cls.model)
        except Exception as exc:
            logger.error(f"Error storing form data: {str(exc)}")
            return None, str(exc)

    @classmethod
    def get_worker_parameters(cls, worker_type: str) -> list[WorkerParameterValue]:
        dpl = DataPersistenceLayer()
        all_parameters = dpl.get_objects(WorkerParameter)
        match = next((wp for wp in all_parameters if wp.id == worker_type), None)
        return match.parameters if match else []

    @classmethod
    def store_form_data(cls, processed_data: dict[str, Any], object_id: int | str = 0):
        try:
            obj = cls.model(**processed_data)
            dpl = DataPersistenceLayer()
            result = dpl.store_object(obj) if object_id == 0 else dpl.update_object(obj, object_id)
            return (result.json(), None) if result.ok else (None, result.json())
        except ValidationError as exc:
            logger.error(format_pydantic_errors(exc, cls.model))
            return None, format_pydantic_errors(exc, cls.model)
        except Exception as exc:
            logger.error(f"Error storing form data: {str(exc)}")
            return None, str(exc)

    @classmethod
    def get_list_template(cls) -> str:
        return cls.get_htmx_list_template() if is_htmx_request() else cls.get_default_template()

    @classmethod
    def get_update_template(cls) -> str:
        return cls.get_htmx_update_template() if is_htmx_request() else cls.get_edit_template()

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
        return base_context

    @classmethod
    def get_template_urls(cls) -> dict[str, str]:
        return {
            "htmx_update_template": cls.get_htmx_update_template(),
            "htmx_list_template": cls.get_htmx_list_template(),
            "update_template": cls.get_update_template(),
            "list_template": cls.get_list_template(),
            "default_template": cls.get_default_template(),
            "sidebar_template": cls.get_sidebar_template(),
        }

    @classmethod
    def get_sidebar_template(cls) -> str:
        return ""

    @classmethod
    def edit_view(cls, object_id: int | str = 0):
        if str(object_id) == "0":
            return render_template(cls.get_update_template(), **cls.get_create_context()), 200
        return render_template(cls.get_update_template(), **cls.get_item_context(object_id)), 200

    @classmethod
    def get_item_context(cls, object_id: int | str) -> dict[str, Any]:
        dpl = DataPersistenceLayer()
        key = cls._get_object_key()
        form_action = f"hx-put={cls.get_edit_route(**{key: object_id})}"
        submit = f"Update {cls.pretty_name()}"

        context = cls._common_context(object_id=object_id)
        context.update(
            {
                "form_error": None,
                "form_action": form_action,
                "submit_text": submit,
            }
        )

        context[cls.model_name()] = dpl.get_object(cls.model, object_id)
        return cls.get_extra_context(context)

    @classmethod
    def get_create_context(cls) -> dict[str, Any]:
        form_action = f"hx-post={cls.get_base_route()}"
        submit = f"Create {cls.pretty_name()}"

        context = cls._common_context()
        context.update(
            {
                "form_error": None,
                "form_action": form_action,
                "submit_text": submit,
            }
        )

        context[cls.model_name()] = cls.model.model_construct()
        return cls.get_extra_context(context)

    @classmethod
    def get_update_context(
        cls,
        object_id: int | str,
        error: str | None = None,
        form_error: str | None = None,
        resp_obj=None,
    ) -> dict[str, Any]:
        context = cls.get_item_context(object_id)
        context.update(
            {
                "error": error,
                "form_error": form_error,
            }
        )

        if resp_obj:
            context[cls.model_name()] = resp_obj.get(cls.model_name())
            if msg := resp_obj.get("message"):
                context["message"] = msg

        return context

    @classmethod
    def get_default_actions(cls) -> list[dict[str, Any]]:
        return [
            {"label": "Edit", "class": "btn-primary", "icon": "pencil-square", "url": cls.get_base_route(), "type": "link"},
            {
                "label": "Delete",
                "icon": "trash",
                "class": "btn-error",
                "method": "delete",
                "url": cls.get_base_route(),
                "hx_target": f"#{cls.model_name()}-table-container",
                "hx_swap": "outerHTML",
                "type": "button",
                "confirm": "Are you sure you want to delete this item?",
            },
        ]

    @classmethod
    def get_view_context(
        cls,
        objects: CacheObject | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        context = cls._common_context(error)
        if objects:
            context[f"{cls.model_plural_name()}"] = objects
        context["actions"] = cls.get_default_actions()
        return cls.get_extra_context(context)

    @classmethod
    def update_view(cls, object_id: int | str = 0):
        logger.debug(f"Updating {cls.model_name()} with ID {object_id} - {request.form}")
        core_response, error = cls.process_form_data(object_id)
        if core_response and not error:
            response = cls.get_notification_from_dict(core_response)
            table, table_response = cls.list_view()
            if table_response == 200:
                response += table
            return response, table_response

        return render_template(
            cls.get_update_template(),
            **cls.get_update_context(object_id, error=error, resp_obj=core_response),
        ), 400

    @classmethod
    def list_view(cls):
        try:
            params = convert_query_params(request.args, PagingData)
            page = PagingData(**params)
            items = DataPersistenceLayer().get_objects(cls.model, page)
            error = None if items else f"No {cls.model_name()} items found"
        except ValidationError as exc:
            logger.exception(format_pydantic_errors(exc, cls.model))
            items, error = None, format_pydantic_errors(exc, cls.model)
        except Exception as exc:
            logger.exception(f"Error retrieving {cls.model_name()} items")
            items, error = None, str(exc)

        if error and is_htmx_request():
            logger.error(f"Error retrieving {cls.model_name()} items: {error}")
            return render_template("notification/index.html", notification={"message": error, "error": True}), 400

        return render_template(cls.get_list_template(), **cls.get_view_context(items, error)), 400 if error else 200

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
            return render_template("errors/404.html", error=f"No {cls.model_name()} items found"), 404

        context = cls._common_context(error)
        context[f"{cls.model_plural_name()}"] = items
        context = cls.get_extra_context(context)
        return render_template(cls.get_list_template(), **context), 200

    @classmethod
    def get_notification_from_response(cls, response: RequestsResponse) -> str:
        """
        Extracts the notification from the response object.
        If the response contains a JSON body and response.ok it extracts the 'message' key otherwise it extracts the 'error' key.
        If it was ok it should render it as a success message, otherwise it should render it as an error message.
        """
        if response.ok and response.json():
            return render_template("notification/index.html", notification={"message": response.json().get("message"), "error": False})
        return render_template("notification/index.html", notification={"message": response.json().get("error"), "error": True})

    @classmethod
    def get_notification_from_dict(cls, response: dict) -> str:
        """
        Extracts the notification from the response object.
        If the response contains a JSON body and response.ok it extracts the 'message' key otherwise it extracts the 'error' key.
        If it was ok it should render it as a success message, otherwise it should render it as an error message.
        """
        if response.get("message"):
            return render_template("notification/index.html", notification={"message": response.get("message"), "error": False})
        return render_template("notification/index.html", notification={"message": response.get("error"), "error": True})

    @classmethod
    def delete_view(cls, object_id: str | int) -> tuple[str, int]:
        core_response = DataPersistenceLayer().delete_object(cls.model, object_id)

        response = cls.get_notification_from_response(core_response)
        table, table_response = cls.list_view()
        if table_response == 200:
            response += table
        return response, core_response.status_code

    @classmethod
    def delete_multiple_view(cls, object_ids: list[str]) -> tuple[str, int]:
        results = []
        results.extend(DataPersistenceLayer().delete_object(cls.model, object_id) for object_id in object_ids)
        response, status_code = cls.list_view()
        if all(r.ok for r in results):
            response += render_template(
                "notification/index.html", notification={"message": "Selected items deleted successfully", "error": False}
            )
            return response, status_code

        response += render_template("notification/index.html", notification={"message": "Failed to delete selected items", "error": True})
        return response, 500

    @classmethod
    def _get_object_key(cls) -> str:
        return f"{cls.model_name().lower()}_id"

    def _get_object_id(self, kwargs: dict) -> int | str | None:
        key = self._get_object_key()
        return kwargs.get(key)

    def get(self, **kwargs) -> tuple[str, int]:
        object_id = self._get_object_id(kwargs)
        if object_id is None:
            return self.list_view()
        return self.edit_view(object_id=object_id)

    def post(self, *args, **kwargs) -> tuple[str, int]:
        return self.update_view(object_id=0)

    def put(self, **kwargs) -> tuple[str, int]:
        object_id = self._get_object_id(kwargs)
        if object_id is None:
            abort(405)
        return self.update_view(object_id=object_id)

    def delete(self, **kwargs):
        if ids := request.form.getlist("ids"):
            return self.delete_multiple_view(object_ids=ids)
        if ids := request.args.getlist("ids"):
            return self.delete_multiple_view(object_ids=ids)
        object_id = self._get_object_id(kwargs) or request.form.get("id")
        if object_id is None:
            abort(405)
        return self.delete_view(object_id=object_id)

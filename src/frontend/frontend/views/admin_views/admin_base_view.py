import json
from typing import Any, ClassVar

from flask import current_app
from flask.typing import ResponseReturnValue
from jinja2 import TemplateNotFound
from models.worker_parameters import parameter_schema

from frontend.auth import admin_required
from frontend.views.base_view import BaseView


class AdminBaseView(BaseView):
    decorators: ClassVar[list[Any]] = [admin_required()]
    base_route: ClassVar[str] = ""
    edit_route: ClassVar[str] = ""
    import_route: ClassVar[str] = ""
    _is_admin: ClassVar[bool] = True
    _show_sidebar: ClassVar[bool] = True
    _read_only: ClassVar[bool] = False

    @classmethod
    def get_sidebar_template(cls) -> str:
        return "partials/admin_sidebar.html"

    @classmethod
    def _common_context(cls, error: str | None = None, object_id: str = "0") -> dict[str, Any]:
        return super()._common_context(error=error, object_id=object_id)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if getattr(cls, "model", None) is None:
            return

        if not cls.base_route:
            cls.base_route = f"admin.{cls.model_plural_name().lower()}"
        if not cls.edit_route and not cls._read_only:
            cls.edit_route = f"admin.edit_{cls.model_name().lower()}"
        if not cls.import_route and not cls._read_only:
            cls.import_route = f"admin.import_{cls.model_plural_name().lower()}"

    @classmethod
    def _fallback_template(cls, path: str, fallback_suffix: str) -> str:
        """
        Return `path` if it exists in the Jinja loader; otherwise fallback to `default/{model_name}{fallback_suffix}`.
        """
        try:
            current_app.jinja_env.get_template(path)
            return path
        except TemplateNotFound:
            return f"default/admin{fallback_suffix}"

    @classmethod
    def submits_via_standard_form(cls) -> bool:
        return not cls._read_only

    @classmethod
    def get_form_action(cls, object_id: str = "0") -> str:
        if not cls.submits_via_standard_form():
            return super().get_form_action(object_id)
        if cls.is_create_object_id(object_id):
            return cls.get_base_route()
        return cls.get_edit_route(**{cls._get_object_key(): object_id})

    @classmethod
    def get_worker_parameters(cls, worker_type: str) -> list[dict[str, Any]]:
        schema = parameter_schema(worker_type)
        definitions = schema.get("$defs", {})
        required = set(schema.get("required", []))
        fields = []
        for name, raw_property in schema.get("properties", {}).items():
            prop = dict(raw_property)
            if reference := prop.pop("$ref", None):
                prop = {**definitions[reference.rsplit("/", 1)[-1]], **prop}
            if variants := prop.get("anyOf"):
                concrete = next((variant for variant in variants if variant.get("type") != "null"), {})
                prop = {**prop, **concrete}
            value = prop.get("default", "")
            if isinstance(value, bool):
                value = "true" if value else "false"
            elif isinstance(value, (dict, list)):
                value = json.dumps(value, separators=(",", ":"))
            widget = prop.get("widget")
            minimum = prop.get("minimum")
            if minimum is None and "exclusiveMinimum" in prop:
                minimum = prop["exclusiveMinimum"] + (1 if prop.get("type") == "integer" else 0)
            maximum = prop.get("maximum")
            if maximum is None and prop.get("type") == "integer" and "exclusiveMaximum" in prop:
                maximum = prop["exclusiveMaximum"] - 1
            field_type = (
                "word-list-table"
                if widget == "word-list-table"
                else "password"
                if prop.get("writeOnly") or prop.get("format") == "password"
                else "cron_interval"
                if widget == "cron"
                else "textarea"
                if widget == "textarea"
                else "switch"
                if prop.get("type") == "boolean"
                else "number"
                if prop.get("type") in {"integer", "number"}
                else "select"
                if prop.get("enum")
                else "text"
            )
            fields.append(
                {
                    "name": name,
                    "label": prop.get("title", name),
                    "description": prop.get("description", ""),
                    "type": field_type,
                    "value": value,
                    "required": name in required,
                    "pattern": prop.get("pattern", ""),
                    "minimum": minimum,
                    "maximum": maximum,
                    "options": [{"id": option, "name": option} for option in prop.get("enum", [])],
                    "widget": widget,
                }
            )
        return fields

    @classmethod
    def handle_submit_error(cls, object_id: str, error: str | None = None, resp_obj: dict | None = None) -> tuple[str, int]:
        if not cls.submits_via_standard_form():
            return super().handle_submit_error(object_id, error=error, resp_obj=resp_obj)
        return cls.render_submitted_form_error(object_id, error=error, resp_obj=resp_obj)

    @classmethod
    def handle_submit_success(cls, object_id: str, core_response: dict) -> ResponseReturnValue:
        if not cls.submits_via_standard_form():
            return super().handle_submit_success(object_id, core_response)
        cls.add_flash_notification(core_response)
        return cls.redirect_htmx(cls.get_submit_redirect_target(object_id, core_response))

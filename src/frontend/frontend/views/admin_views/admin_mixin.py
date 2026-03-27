from typing import cast

from flask import current_app
from flask.typing import ResponseReturnValue
from jinja2 import TemplateNotFound

from frontend.auth import admin_required


class AdminMixin:
    decorators = [admin_required()]
    _is_admin = True
    _show_sidebar = True
    _read_only = False

    @classmethod
    def get_sidebar_template(cls) -> str:
        return "partials/admin_menu.html"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        from frontend.views.base_view import BaseView

        bv = cast(type[BaseView], cls)

        if getattr(bv, "model", None) is None:
            return

        if not getattr(bv, "base_route", None):
            bv.base_route = f"admin.{bv.model_plural_name().lower()}"
        if not getattr(bv, "edit_route", None) and not bv._read_only:
            bv.edit_route = f"admin.edit_{bv.model_name().lower()}"
        if not getattr(bv, "import_route", None) and not bv._read_only:
            bv.import_route = f"admin.import_{bv.model_plural_name().lower()}"

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
    def get_form_action(cls, object_id: int | str = 0) -> str:
        if not cls.submits_via_standard_form():
            return super(AdminMixin, cls).get_form_action(object_id)
        if str(object_id) == "0":
            return cls.get_base_route()
        return cls.get_edit_route(**{cls._get_object_key(): object_id})

    @classmethod
    def handle_submit_error(cls, object_id: int | str, error: str | None = None, resp_obj: dict | None = None) -> tuple[str, int]:
        if not cls.submits_via_standard_form():
            return super(AdminMixin, cls).handle_submit_error(object_id, error=error, resp_obj=resp_obj)
        return cls.render_submitted_form_error(object_id, error=error, resp_obj=resp_obj)

    @classmethod
    def handle_submit_success(cls, object_id: int | str, core_response: dict) -> ResponseReturnValue:
        if not cls.submits_via_standard_form():
            return super(AdminMixin, cls).handle_submit_success(object_id, core_response)
        cls.add_flash_notification(core_response)
        return cls.redirect_htmx(cls.get_submit_redirect_target(object_id, core_response))

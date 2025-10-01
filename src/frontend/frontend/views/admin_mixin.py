from typing import cast
from flask import current_app
from jinja2 import TemplateNotFound


class AdminMixin:
    _is_admin = True

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

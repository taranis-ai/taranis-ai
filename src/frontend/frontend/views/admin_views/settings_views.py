from flask import render_template, request, url_for
from models.admin import Settings

from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.i18n import get_timezone_options
from frontend.log import logger
from frontend.utils.form_data_parser import parse_formdata
from frontend.views.admin_views.admin_mixin import AdminMixin
from frontend.views.base_view import BaseView


class SettingsView(AdminMixin, BaseView):
    model = Settings
    htmx_list_template = "settings/index.html"
    htmx_update_template = "settings/index.html"
    default_template = "settings/index.html"
    base_route = "admin_settings.settings"
    edit_route = "admin_settings.settings"
    _read_only = True
    _index = 190

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict:
        dpl = DataPersistenceLayer()
        base_context["_is_admin"] = cls._is_admin
        base_context["settings"] = dpl.get_first(Settings)
        base_context["timezone_options"] = get_timezone_options()
        base_context["frontend_actions"] = [
            {
                "label": "Invalidate Cache",
                "url": url_for("base.invalidate_cache"),
            }
        ]
        return base_context

    @classmethod
    def model_plural_name(cls) -> str:
        """Returns the plural name of the model class."""
        return f"{cls.model._model_name}"

    @classmethod
    def settings_action(cls, action_url, method="download"):
        logger.debug(f"Calling settings action: {action_url}")

        if method == "download":
            response = CoreApi().api_download(action_url)
            if not response.ok:
                logger.error(f"Failed to download file from {action_url}: {response.status_code} - {response.text}")
                notification = cls.get_notification_from_response(response)
                static_view, static_response = cls.static_view()
                notification += static_view
                return notification, static_response
            return CoreApi().stream_proxy(response, "stories_export.json")

        if method == "patch":
            payload = parse_formdata(request.form) if request.form else None
            response = CoreApi().api_patch(action_url, json_data=payload)
            notification = cls.get_notification_from_response(response)
            static_view, static_response = cls.static_view()
            notification += static_view
            return notification, static_response

        if request.form:
            response, error = cls.process_form_data(object_id="0")
            message = response.get("message") if response else error
            notification = render_template("notification/index.html", notification={"message": message, "error": bool(error)})
        else:
            response = CoreApi().api_post(action_url)
            notification = cls.get_notification_from_response(response)

        static_view, static_response = cls.static_view()
        notification += static_view
        return notification, static_response

    def get(self, **kwargs):
        return self.static_view()

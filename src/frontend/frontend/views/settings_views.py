from flask import request, render_template, Response

from models.admin import Settings
from frontend.views.base_view import BaseView
from frontend.log import logger
from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer


class SettingsView(BaseView):
    model = Settings
    htmx_list_template = "settings/index.html"
    htmx_update_template = "settings/index.html"
    default_template = "settings/index.html"
    base_route = "admin_settings.settings"
    edit_route = "admin_settings.settings"
    _index = 190

    @classmethod
    def get_extra_context(cls, object_id: int | str):
        dpl = DataPersistenceLayer()
        return {"settings": dpl.get_objects(Settings)}

    @classmethod
    def model_plural_name(cls) -> str:
        """Returns the plural name of the model class."""
        return f"{cls.model._model_name}"

    @classmethod
    def settings_action(cls, action_url, method="download"):
        logger.debug(f"Calling settings action: {action_url}")
        error = None

        if method == "post":
            if request.form:
                return cls.update_view(object_id=0)
            else:
                response = CoreApi().api_post(action_url)
        else:
            response = CoreApi().api_download(action_url)

        if not response or not response.ok:
            error = "Failed to call settings action: "
            error += response.json().get("error", action_url)
            return render_template("partials/error.html", error=error), response.status_code if response else 500

        if method == "post":
            return Response(status=200, headers={"HX-Refresh": "true"})
        else:
            return CoreApi.stream_proxy(response, "stories_export.json")

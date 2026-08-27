from typing import Any, ClassVar

from flask import abort, render_template, request
from flask.typing import ResponseReturnValue
from models.dashboard import Dashboard
from requests import RequestException

from frontend.auth import auth_required
from frontend.core_api import CoreApi
from frontend.log import logger
from frontend.views.admin_views.admin_base_view import AdminBaseView


class AdminNotificationView(AdminBaseView):
    decorators: ClassVar[list[Any]] = [auth_required("ADMIN_OPERATIONS")]
    model = Dashboard
    icon = "bell"
    htmx_list_template = "admin_notifications/index.html"
    default_template = "admin_notifications/index.html"
    base_route = "admin.notifications"
    _read_only = True
    _index = 20

    @classmethod
    def pretty_name(cls) -> str:
        return "Notifications"

    @classmethod
    def static_view(cls):
        status = CoreApi().api_get("/realtime/clients")
        if not isinstance(status, dict):
            status = {
                "num_clients": 0,
                "num_users": 0,
                "clients": [],
                "error": "Connected client information is unavailable.",
            }
        return render_template(cls.get_list_template(), status=status, **cls._common_context()), 200

    def get(self, **kwargs: Any) -> ResponseReturnValue:
        return self.static_view()

    def post(self, **kwargs: Any) -> ResponseReturnValue:
        try:
            response = CoreApi().api_post(
                "/realtime/broadcast",
                json_data={"message": request.form.get("message", "")},
            )
        except RequestException:
            logger.exception("Failed to send broadcast notification")
            return self.render_response_notification({"error": "Broadcast could not be sent"}), 502
        return self.get_notification_from_response(response), response.status_code

    def put(self, **kwargs: Any) -> ResponseReturnValue:
        return abort(405)

    def delete(self, **kwargs: Any) -> tuple[str, int]:
        return abort(405)

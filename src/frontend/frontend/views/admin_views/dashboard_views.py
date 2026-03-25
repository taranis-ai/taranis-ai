from flask import abort, render_template
from models.dashboard import Dashboard

from frontend.config import Config
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.views.admin_views.admin_mixin import AdminMixin
from frontend.views.base_view import BaseView


class AdminDashboardView(AdminMixin, BaseView):
    model = Dashboard
    icon = "home"
    htmx_list_template = "admin_dashboard/index.html"
    htmx_update_template = "admin_dashboard/index.html"
    default_template = "admin_dashboard/index.html"
    base_route = "admin.dashboard"
    _read_only = True
    _index = 10

    @classmethod
    def pretty_name(cls) -> str:
        return "Admin Dashboard"

    @classmethod
    def static_view(cls):
        error = None
        data_persistence = DataPersistenceLayer()
        try:
            dashboard = data_persistence.get_first(Dashboard)
        except Exception as exc:
            dashboard = None
            error = str(exc)

        if error or not dashboard:
            logger.error(f"Error retrieving {cls.model_name()} items: {error}")
            return render_template("errors/404.html", error="No Dashboard items found"), 404
        template = cls.get_list_template()
        context = {
            "data": dashboard,
            "dashboard_health": cls.get_dashboard_health(dashboard),
            "release_info": cls.get_release_info(data_persistence),
            "health_badge_classes": cls.get_health_badge_classes(),
            **cls._common_context(error),
        }
        return render_template(template, **context), 200

    @classmethod
    def get_build_info(cls) -> dict[str, str]:
        result = {"build_date": Config.BUILD_DATE.isoformat()}
        if Config.GIT_INFO:
            result |= Config.GIT_INFO
        return result

    @classmethod
    def get_core_build_info(cls, data_persistence: DataPersistenceLayer) -> dict[str, str] | None:
        endpoint = f"{cls.model._core_endpoint}/build-info"
        build_info = data_persistence.api.api_get(endpoint)
        if isinstance(build_info, dict):
            return build_info

        logger.warning("Failed to retrieve core build info for admin dashboard")
        return None

    @classmethod
    def get_release_info(cls, data_persistence: DataPersistenceLayer) -> dict[str, dict[str, str] | None]:
        return {
            "core": cls.get_core_build_info(data_persistence),
            "frontend": cls.get_build_info(),
        }

    @staticmethod
    def get_health_badge_classes() -> dict[str, str]:
        return {
            "up": "badge-success",
            "down": "badge-error",
            "n/a": "badge-neutral",
        }

    @staticmethod
    def get_dashboard_health(dashboard: Dashboard) -> dict[str, bool | dict[str, str]]:
        if health_status := dashboard.health_status:
            return {"healthy": bool(health_status.healthy), "services": health_status.services.model_dump()}

        return {"healthy": False, "services": {"database": "n/a", "broker": "n/a", "workers": "n/a"}}

    def get(self, **kwargs):
        return self.static_view()

    def post(self):
        return abort(405)

    def put(self, **kwargs):
        return abort(405)

    def delete(self, **kwargs):
        return abort(405)

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
        try:
            dashboard = DataPersistenceLayer().get_objects(cls.model)
        except Exception as exc:
            dashboard = None
            error = str(exc)

        if error or not dashboard:
            logger.error(f"Error retrieving {cls.model_name()} items: {error}")
            return render_template("errors/404.html", error="No Dashboard items found"), 404
        template = cls.get_list_template()
        context = {
            "data": dashboard[0],
            "dashboard_health": cls.get_dashboard_health(dashboard[0]),
            "build_info": cls.get_build_info(),
            "health_badge_classes": cls.get_health_badge_classes(),
            **cls._common_context(error),
        }
        return render_template(template, **context), 200

    @classmethod
    def get_build_info(cls):
        result = {"build_date": Config.BUILD_DATE.isoformat()}
        if Config.GIT_INFO:
            result |= Config.GIT_INFO
        return result

    @staticmethod
    def get_health_badge_classes() -> dict[str, str]:
        return {
            "up": "badge-success",
            "down": "badge-error",
            "n/a": "badge-neutral",
        }

    @staticmethod
    def get_dashboard_health(dashboard: Dashboard) -> dict[str, bool | dict[str, str]] | None:
        health_status = dashboard.get("health_status") if isinstance(dashboard, dict) else getattr(dashboard, "health_status", None)
        if not health_status:
            return None

        services = getattr(health_status, "services", {})
        if isinstance(health_status, dict):
            services = health_status.get("services", {})
            healthy = health_status.get("healthy", False)
        else:
            healthy = getattr(health_status, "healthy", False)

        if hasattr(services, "model_dump"):
            services = services.model_dump()
        elif not isinstance(services, dict):
            services = {}

        return {"healthy": bool(healthy), "services": services}

    def get(self, **kwargs):
        return self.static_view()

    def post(self):
        return abort(405)

    def put(self, **kwargs):
        return abort(405)

    def delete(self, **kwargs):
        return abort(405)

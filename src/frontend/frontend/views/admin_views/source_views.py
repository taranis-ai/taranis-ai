import json
from typing import Any, Literal

from flask import Response, render_template, request, url_for
from models.admin import Job, OSINTSource, TaskResult
from models.dashboard import Dashboard
from models.types import COLLECTOR_TYPES

from frontend.auth import auth_required
from frontend.config import Config
from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.filters import render_icon, render_source_parameter, render_truncated, render_worker_status
from frontend.log import logger
from frontend.views.admin_views.admin_mixin import AdminMixin
from frontend.views.base_view import BaseView


class SourceView(AdminMixin, BaseView):
    model = OSINTSource
    icon = "book-open"
    import_route = "admin.import_osint_sources"
    _index = 63

    collector_types = {
        member.name.lower(): {"id": member.name.lower(), "name": " ".join(part.capitalize() for part in member.name.split("_"))}
        for member in COLLECTOR_TYPES
    }

    @classmethod
    def get_admin_menu_badge(cls) -> int:
        if dashboard := DataPersistenceLayer().get_first(Dashboard):
            if worker_status := dashboard.worker_status:
                return worker_status.get("collector_task", {}).get("failures", 0)

        return 0

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
        parameters = {}
        parameter_values = {}

        osint_source_actions = [
            {
                "label": "Preview",
                "icon": "eye",
                "method": "post",
                "url": url_for("admin.osint_source_preview", osint_source_id=""),
                "type": "link",
            },
            {
                "label": "Collect",
                "icon": "arrows-pointing-in",
                "method": "post",
                "url": url_for("admin.collect_osint_source", osint_source_id=""),
                "hx_target_error": "#notification-bar",
                "hx_target": "#notification-bar",
                "hx_swap": "outerHTML",
                "confirm": None,
            },
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
                "confirm": "Are you sure you want to delete this OSINT Source?",
                "data_attr": "data-swal-confirm=true",
            },
        ]

        collector = base_context.get(cls.model_name())
        if collector and (collector_type := collector.type):
            parameter_values = collector.parameters
            parameters = cls.get_worker_parameters(worker_type=collector_type.name.lower())

        base_context["parameters"] = parameters
        base_context["parameter_values"] = parameter_values
        base_context["collector_types"] = cls.collector_types.values()
        base_context["actions"] = osint_source_actions
        return base_context

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "Icon", "field": "icon", "sortable": False, "renderer": render_icon},
            {"title": "State", "field": "status", "sortable": True, "renderer": render_worker_status},
            {
                "title": "Name",
                "field": "name",
                "sortable": True,
                "renderer": render_truncated,
                "render_args": {"field": "name"},
            },
            {"title": "Feed", "field": "parameters", "sortable": False, "renderer": render_source_parameter},
        ]

    @classmethod
    def get_osint_source_parameters_view(cls, osint_source_id: str, collector_type: str):
        if not osint_source_id and not collector_type:
            logger.warning("No OSINT source ID or collector type provided.")

        parameters = cls.get_worker_parameters(collector_type)

        return render_template("partials/worker_parameters.html", parameters=parameters)

    @classmethod
    def import_view(cls, error=None):
        return render_template(f"{cls.model_name().lower()}/{cls.model_name().lower()}_import.html", error=error)

    @classmethod
    def import_post_view(cls):
        sources = request.files.get("file")
        if not sources:
            return cls.import_view("No file or organization provided")
        data = sources.read()
        json_data = json.loads(data)

        response = CoreApi().import_sources(json_data)

        if not response:
            error = "Failed to import sources"
            return cls.import_view(error)

        DataPersistenceLayer().invalidate_cache_by_object(OSINTSource)
        return Response(status=200, headers={"HX-Refresh": "true"})

    @classmethod
    def export_view(cls):
        source_ids = request.args.getlist("ids")
        core_resp = CoreApi().export_sources({"ids": source_ids})

        if not core_resp:
            logger.debug(f"Failed to fetch sources from: {Config.TARANIS_CORE_URL}")
            return f"Failed to fetch sources from: {Config.TARANIS_CORE_URL}", 500

        return CoreApi.stream_proxy(core_resp, "sources_export.json")

    @classmethod
    def load_default_osint_sources(cls):
        response = CoreApi().load_default_osint_sources()
        if not response:
            logger.error("Failed to load default OSINT sources")
            return render_template("notification/index.html", notification={"message": "Failed to load default OSINT sources", "error": True})

        response = CoreApi().import_sources(response)

        if not response.ok:
            error = response.json().get("error", "Unknown error")
            error_message = f"Failed to import default OSINT sources: {error}"
            logger.error(error_message)
            return render_template("notification/index.html", notification={"message": error_message, "error": True})

        DataPersistenceLayer().invalidate_cache_by_object(OSINTSource)
        items = DataPersistenceLayer().get_objects(cls.model)
        return render_template(cls.get_list_template(), **cls.get_view_context(items))

    @classmethod
    def _collect_source_view(cls, response):
        if not response:
            logger.error("Failed to start OSINT source collection")
            notification, status = (
                render_template(
                    "notification/index.html", notification={"message": "Failed to start OSINT source collection", "error": True}
                ),
                500,
            )
        else:
            notification, status = (
                render_template(
                    "notification/index.html",
                    notification={
                        "message": "OSINT source collection started successfully",
                        "icon": "check-circle",
                        "class": "alert-success",
                    },
                ),
                200,
            )

        table, table_response = cls.render_list()
        status = table_response if table_response != 200 else status
        return notification + table, status

    @classmethod
    def collect_osint_source(cls, osint_source_id: str):
        response = CoreApi().collect_osint_source(osint_source_id)
        return cls._collect_source_view(response)

    @classmethod
    def collect_all_osint_sources(cls):
        response = CoreApi().collect_all_osint_sources()
        return cls._collect_source_view(response)

    @classmethod
    @auth_required()
    def get_osint_source_preview_view(cls, osint_source_id: str):
        task_result = None
        if response := CoreApi().get_osint_source_preview(osint_source_id):
            task_result = TaskResult(**response)
        logger.debug(f"Task result for OSINT source preview: {task_result}")
        return render_template("osint_source/osint_source_preview.html", task_result=task_result)

    @classmethod
    def delete_view(cls, object_id: str | int) -> tuple[str, int]:
        if request.args.get("force") == "true":
            logger.warning(f"Force deleting OSINT source {object_id}")
            return super().delete_view(f"{object_id}{'?force=true'}")
        return super().delete_view(object_id)

    @classmethod
    @auth_required()
    def toggle_osint_source_state(cls, osint_source_id: str, new_state: Literal["enabled", "disabled"]) -> tuple[str, int]:
        dpl = DataPersistenceLayer()

        response = CoreApi().toggle_osint_source(osint_source_id, new_state)
        if not response:
            logger.error(f"Failed to toggle OSINT source state for {osint_source_id}")
            return render_template(
                "notification/index.html", notification={"message": "Failed to toggle OSINT source state", "error": True}
            ), 500

        dpl.invalidate_cache_by_object(OSINTSource)
        dpl.invalidate_cache_by_object(Job)
        notification = render_template(
            "notification/index.html",
            notification={"message": "OSINT source state updated successfully", "icon": "check-circle", "class": "alert-success"},
        )
        osint_source = dpl.get_object(OSINTSource, osint_source_id)
        state_button = render_template("osint_source/state_button.html", osint_source=osint_source)

        return notification + state_button, 200

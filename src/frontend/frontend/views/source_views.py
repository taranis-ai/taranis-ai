import json
from typing import Any, Literal
from flask import render_template, request, Response, url_for

from models.admin import OSINTSource, WorkerParameter, WorkerParameterValue, TaskResult
from models.types import COLLECTOR_TYPES
from frontend.cache_models import CacheObject
from frontend.views.base_view import BaseView
from frontend.filters import render_icon, render_source_parameter, render_state, render_truncated
from frontend.log import logger
from frontend.data_persistence import DataPersistenceLayer
from frontend.core_api import CoreApi
from frontend.config import Config
from frontend.auth import auth_required


class SourceView(BaseView):
    model = OSINTSource
    icon = "book-open"
    import_route = "admin.import_osint_sources"
    _index = 63

    collector_types = {
        member.name.lower(): {"id": member.name.lower(), "name": " ".join(part.capitalize() for part in member.name.split("_"))}
        for member in COLLECTOR_TYPES
    }

    @classmethod
    def get_worker_parameters(cls, collector_type: str) -> list[WorkerParameterValue]:
        dpl = DataPersistenceLayer()
        all_parameters = dpl.get_objects(WorkerParameter)
        match = next((wp for wp in all_parameters if wp.id == collector_type), None)
        return match.parameters if match else []

    @classmethod
    def get_view_context(cls, objects: CacheObject | None = None, error: str | None = None) -> dict[str, Any]:
        if objects is not None:
            filtered = [obj for obj in (objects or []) if isinstance(obj, OSINTSource) and obj.id != "manual"]
            objects = CacheObject(
                filtered,
                page=objects.page,
                limit=objects.limit,
                order=objects.order,
                links=objects._links,
                total_count=len(filtered),
            )
        return super().get_view_context(objects, error)

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
                "type": "function",
                "icon": "trash",
                "function": "delete_osint_source",
                "url": cls.get_base_route(),
            },
        ]

        collector = base_context.get(cls.model_name())
        if collector and (collector_type := collector.type):
            parameter_values = collector.parameters
            parameters = cls.get_worker_parameters(collector_type=collector_type.name.lower())

        base_context["parameters"] = parameters
        base_context["parameter_values"] = parameter_values
        base_context["collector_types"] = cls.collector_types.values()
        base_context["actions"] = osint_source_actions
        return base_context

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "Icon", "field": "icon", "sortable": False, "renderer": render_icon},
            {"title": "State", "field": "state", "sortable": False, "renderer": render_state},
            {
                "title": "Name",
                "field": "name",
                "sortable": True,
                "renderer": render_truncated,
                "render_args": {"field": "name"},
            },
            {"title": "Feed", "field": "parameters", "sortable": True, "renderer": render_source_parameter},
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
        core_resp = CoreApi().export_sources(source_ids)

        if not core_resp:
            logger.debug(f"Failed to fetch users from: {Config.TARANIS_CORE_URL}")
            return f"Failed to fetch users from: {Config.TARANIS_CORE_URL}", 500

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
    def collect_osint_source(cls, osint_source_id: str):
        response = CoreApi().collect_osint_source(osint_source_id)
        if not response:
            logger.error("Failed to start OSINT source collection")
            return render_template(
                "notification/index.html", notification={"message": "Failed to start OSINT source collection", "error": True}
            ), 500
        return render_template(
            "notification/index.html",
            notification={"message": "OSINT source collection started successfully", "icon": "check-circle", "class": "alert-success"},
        ), 200

    @classmethod
    def collect_all_osint_sources(cls):
        response = CoreApi().collect_all_osint_sources()
        if not response:
            logger.error("Failed to start OSINT sources collection")
            return render_template(
                "notification/index.html", notification={"message": "Failed to start OSINT sources collection", "error": True}
            ), 500
        return render_template(
            "notification/index.html",
            notification={"message": "OSINT sources collection started successfully", "icon": "check-circle", "class": "alert-success"},
        ), 200

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
        object_id_with_params = f"{object_id}{'?force=true' if request.args.get('force') == 'true' else ''}"
        response = DataPersistenceLayer().delete_object(cls.model, object_id_with_params)
        return render_template("notification/swal.html", response=response.json(), is_success=response.ok), response.status_code

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
        notification = render_template(
            "notification/index.html",
            notification={"message": "OSINT source state updated successfully", "icon": "check-circle", "class": "alert-success"},
        )
        osint_source = dpl.get_object(OSINTSource, osint_source_id)
        state_button = render_template("osint_source/state_button.html", osint_source=osint_source)

        return notification + state_button, 200

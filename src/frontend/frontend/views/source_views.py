import json
from typing import Any
from flask import render_template, request, Response

from models.admin import OSINTSource, WorkerParameter, WorkerParameterValue
from models.types import COLLECTOR_TYPES
from frontend.cache_models import CacheObject
from frontend.views.base_view import BaseView
from frontend.filters import render_icon, render_source_parameter, render_state
from frontend.log import logger
from frontend.data_persistence import DataPersistenceLayer
from frontend.core_api import CoreApi
from frontend.config import Config


class SourceView(BaseView):
    model = OSINTSource
    icon = "book-open"
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
    def get_extra_context(cls, object_id: int | str) -> dict[str, Any]:
        dpl = DataPersistenceLayer()
        parameters = {}
        parameter_values = {}
        if str(object_id) != "0" and object_id:
            if collector := dpl.get_object(OSINTSource, object_id):
                if collector_type := collector.type:
                    parameter_values = collector.parameters
                    parameters = cls.get_worker_parameters(collector_type=collector_type.name.lower())

        return {
            "collector_types": cls.collector_types.values(),
            "parameter_values": parameter_values,
            "parameters": parameters,
        }

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "Icon", "field": "icon", "sortable": False, "renderer": render_icon},
            {"title": "State", "field": "state", "sortable": False, "renderer": render_state},
            {"title": "Name", "field": "name", "sortable": True, "renderer": None},
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
        data = json.loads(data)
        data = json.dumps(data["data"])

        response = CoreApi().import_sources(json.loads(data))

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
            return render_template("partials/error.html", error="Failed to load default OSINT sources")

        response = CoreApi().import_sources(response)

        if not response.ok:
            error = response.json().get("error", "Unknown error")
            error_message = f"Failed to import default OSINT sources: {error}"
            logger.error(error_message)
            return render_template("partials/error.html", error=error_message)

        DataPersistenceLayer().invalidate_cache_by_object(OSINTSource)
        items = DataPersistenceLayer().get_objects(cls.model)
        return render_template(cls.get_list_template(), **cls.get_view_context(items))

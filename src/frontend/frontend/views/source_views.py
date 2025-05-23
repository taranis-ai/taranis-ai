from typing import Any
from flask import render_template

from models.admin import OSINTSource, WorkerParameter, WorkerParameterValue
from models.types import COLLECTOR_TYPES
from frontend.views.base_view import BaseView
from frontend.filters import render_icon, render_source_parameter, render_state
from frontend.log import logger
from frontend.data_persistence import DataPersistenceLayer


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
    def get_extra_context(cls, object_id: int | str) -> dict[str, Any]:
        dpl = DataPersistenceLayer()
        parameters = []
        if str(object_id) != "0" and object_id:
            if collector := dpl.get_object(OSINTSource, object_id):
                collector_type = collector.type  # type: ignore
                parameters = cls.get_worker_parameters(f"{collector_type}")

        return {"collector_types": cls.collector_types.values(), "parameters": parameters}

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

        return render_template("osint_source/osint_source_parameters.html", parameters=parameters)

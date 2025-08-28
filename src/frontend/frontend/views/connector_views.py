from frontend.views.base_view import BaseView
from models.admin import Connector
from models.types import CONNECTOR_TYPES
from frontend.filters import render_icon, render_source_parameter, render_worker_status, render_truncated

from typing import Any


class ConnectorView(BaseView):
    model = Connector
    icon = "link"
    _index = 115

    _read_only = True  # TODO: Remove this when we implement create/update/delete for Connectors

    connector_types = {
        member.name.lower(): {"id": member.name.lower(), "name": " ".join(part.capitalize() for part in member.name.split("_"))}
        for member in CONNECTOR_TYPES
    }

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
        parameters = {}
        parameter_values = {}

        connector = base_context.get(cls.model_name())
        if connector and (connector_type := connector.type):
            parameter_values = connector.parameters
            parameters = cls.get_worker_parameters(worker_type=connector_type.name.lower())

        base_context["parameters"] = parameters
        base_context["parameter_values"] = parameter_values
        base_context["connector_types"] = cls.connector_types.values()
        return base_context

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "Icon", "field": "icon", "sortable": False, "renderer": render_icon},
            {"title": "State", "field": "state", "sortable": False, "renderer": render_worker_status},
            {
                "title": "Name",
                "field": "name",
                "sortable": True,
                "renderer": render_truncated,
                "render_args": {"field": "name"},
            },
            {"title": "Feed", "field": "parameters", "sortable": True, "renderer": render_source_parameter},
        ]

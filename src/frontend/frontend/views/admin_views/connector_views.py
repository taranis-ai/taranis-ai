from typing import Any, ClassVar

from flask import render_template
from models.admin import Connector
from models.types import CONNECTOR_TYPES

from frontend.config import Config
from frontend.filters import render_icon, render_source_parameter, render_truncated, render_worker_status
from frontend.log import logger
from frontend.views.admin_views.admin_base_view import AdminBaseView


class ConnectorView(AdminBaseView):
    model = Connector
    icon = "link"
    _index = 115

    connector_types: ClassVar[dict[str, dict[str, str]]] = {
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
        base_context["worker_parameters_selected"] = bool(connector and connector.type)
        base_context["connector_types"] = cls.connector_types.values()
        base_context["secret_reveal_url"] = (
            f"{Config.TARANIS_BASE_PATH.rstrip('/')}/api/config/parameter-secrets/connectors/{connector.id}"
            if connector and connector.id
            else ""
        )
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

    @classmethod
    def get_connector_parameters_view(cls, connector_id: str, connector_type: str):
        connector_type = connector_type.lower().strip()
        if not connector_id and not connector_type:
            logger.warning("No connector ID or type provided.")

        parameters = cls.get_worker_parameters(worker_type=connector_type)
        return render_template("partials/worker_parameters.html", parameters=parameters, worker_parameters_selected=True)

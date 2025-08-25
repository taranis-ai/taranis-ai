from frontend.views.base_view import BaseView
from models.admin import Connector
from frontend.filters import render_icon, render_source_parameter, render_worker_status, render_truncated

from typing import Any


class ConnectorView(BaseView):
    model = Connector
    icon = "link"
    _index = 115

    _read_only = True  # TODO: Remove this when we implement create/update/delete for Connectors

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

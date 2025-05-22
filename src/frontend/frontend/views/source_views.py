from typing import Any
from flask import render_template

from models.admin import OSINTSource, Worker
from frontend.views.base_view import BaseView
from frontend.filters import render_icon, render_source_parameter, render_state
from frontend.log import logger
from frontend.data_persistence import DataPersistenceLayer


class SourceView(BaseView):
    model = OSINTSource
    icon = "book-open"
    _index = 63

    @classmethod
    def get_extra_context(cls, object_id: int | str) -> dict[str, Any]:
        dpl = DataPersistenceLayer()
        return {"collector_types": dpl.get_objects(Worker)}

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

        parameters = []

        return render_template("osint_source/osint_source_parameters.html", parameters=parameters)

from typing import Any
from frontend.views.base_view import BaseView
from models.admin import ReportItemType
from models.admin import Attribute
from frontend.data_persistence import DataPersistenceLayer


class ReportItemTypeView(BaseView):
    model = ReportItemType
    icon = "presentation-chart-bar"
    _index = 120

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "ID", "field": "id", "sortable": False, "renderer": None},
            {"title": "Title", "field": "title", "sortable": True, "renderer": None},
            {"title": "Description", "field": "description", "sortable": True, "renderer": None},
        ]

    @classmethod
    def get_extra_context(cls, object_id: int | str):
        dpl = DataPersistenceLayer()
        return {"attributes": [p.model_dump() for p in dpl.get_objects(Attribute)]}

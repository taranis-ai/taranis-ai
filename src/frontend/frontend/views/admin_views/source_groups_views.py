from typing import Any

from models.admin import OSINTSource, OSINTSourceGroup, WordList

from frontend.data_persistence import DataPersistenceLayer
from frontend.filters import render_count
from frontend.log import logger
from frontend.views.admin_views.admin_mixin import AdminMixin
from frontend.views.base_view import BaseView


class SourceGroupView(AdminMixin, BaseView):
    model = OSINTSourceGroup
    icon = "building-library"
    _index = 65

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
        dpl = DataPersistenceLayer()
        word_lists = []
        osint_sources = []

        try:
            word_lists = [
                w.model_dump(include={"id", "name"}, mode="json") for w in dpl.get_objects(WordList) if "COLLECTOR_INCLUDELIST" in w.usage
            ]
        except Exception:
            logger.exception("Error retrieving word lists for source group form")

        try:
            osint_sources = [p.model_dump(include={"id", "name"}, mode="json") for p in dpl.get_objects(OSINTSource)]
        except Exception:
            logger.exception("Error retrieving OSINT sources for source group form")

        base_context["osint_sources"] = osint_sources
        base_context["word_lists"] = word_lists
        return base_context

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        columns = super().get_columns()
        return columns + [
            {
                "title": "Sources",
                "field": "osint_sources",
                "sortable": False,
                "renderer": render_count,
                "render_args": {"field": "osint_sources"},
            },
        ]

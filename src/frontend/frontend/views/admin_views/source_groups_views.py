from typing import Any

from models.admin import OSINTSourceGroup, OSINTSourceGroupOptions
from werkzeug.exceptions import HTTPException

from frontend.data_persistence import DataPersistenceLayer
from frontend.filters import render_count
from frontend.log import logger
from frontend.views.admin_views.admin_base_view import AdminBaseView


class SourceGroupView(AdminBaseView):
    model = OSINTSourceGroup
    icon = "building-library"
    _index = 65

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
        options = OSINTSourceGroupOptions()
        try:
            options = DataPersistenceLayer().get_object(OSINTSourceGroupOptions) or options
        except HTTPException:
            raise
        except Exception:
            logger.exception("Error retrieving source group options")

        base_context["osint_sources"] = options.osint_sources
        base_context["word_lists"] = options.word_lists
        return base_context

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        columns = super().get_columns()
        return [
            *columns,
            {
                "title": "Sources",
                "field": "osint_sources",
                "sortable": False,
                "renderer": render_count,
                "render_args": {"field": "osint_sources"},
            },
        ]

from typing import Any
from models.admin import OSINTSourceGroup, OSINTSource, WordList
from frontend.views.base_view import BaseView
from frontend.data_persistence import DataPersistenceLayer


class SourceGroupView(BaseView):
    model = OSINTSourceGroup
    icon = "building-library"
    _index = 65

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
        dpl = DataPersistenceLayer()
        word_lists = [w.model_dump(mode="json") for w in dpl.get_objects(WordList) if "COLLECTOR_INCLUDELIST" in w.usage]

        base_context["osint_sources"] = [p.model_dump(mode="json") for p in dpl.get_objects(OSINTSource)]
        base_context["word_lists"] = word_lists
        return base_context

from models.admin import OSINTSourceGroup, OSINTSource, WordList
from frontend.views.base_view import BaseView
from frontend.data_persistence import DataPersistenceLayer


class SourceGroupView(BaseView):
    model = OSINTSourceGroup
    icon = "building-library"
    _index = 65

    @classmethod
    def get_extra_context(cls, object_id: int | str):
        dpl = DataPersistenceLayer()
        word_lists = [w.model_dump() for w in dpl.get_objects(WordList) if "COLLECTOR_INCLUDELIST" in w.usage]

        return {
            "osint_sources": [p.model_dump() for p in dpl.get_objects(OSINTSource)],
            "word_lists": word_lists,
        }

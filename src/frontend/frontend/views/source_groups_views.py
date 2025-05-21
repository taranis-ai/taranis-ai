from models.admin import OSINTSourceGroup, OSINTSource
from frontend.views.base_view import BaseView
from frontend.data_persistence import DataPersistenceLayer


class SourceGroupView(BaseView):
    model = OSINTSourceGroup
    icon = "building-library"
    _index = 65

    @classmethod
    def get_extra_context(cls, object_id: int | str):
        dpl = DataPersistenceLayer()
        return {"osint_sources": [p.model_dump() for p in dpl.get_objects(OSINTSource)]}

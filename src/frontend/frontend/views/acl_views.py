from typing import Any

from models.admin import ACL, Role
from frontend.data_persistence import DataPersistenceLayer
from frontend.views.base_view import BaseView


class ACLView(BaseView):
    model = ACL
    _index = 50
    icon = "lock-closed"

    @classmethod
    def get_extra_context(cls, object_id: int | str) -> dict[str, Any]:
        dpl = DataPersistenceLayer()
        return {"roles": [p.model_dump() for p in dpl.get_objects(Role)]}

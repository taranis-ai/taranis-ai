# role_views.py
from models.admin import ACL, Role
from frontend.data_persistence import DataPersistenceLayer
from frontend.views.base_view import BaseView


class ACLView(BaseView):
    model = ACL

    @classmethod
    def get_extra_context(cls, object_id: int):
        dpl = DataPersistenceLayer()
        return {"roles": [p.model_dump() for p in dpl.get_objects(Role)]}

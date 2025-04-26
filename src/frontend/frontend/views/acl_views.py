# role_views.py
from frontend.models import ACL, Role
from frontend.data_persistence import DataPersistenceLayer
from frontend.views.base_view import BaseView


class ACLView(BaseView):
    model = ACL
    htmx_list_template = "acl/acl_table.html"
    htmx_update_template = "acl/acl_form.html"
    default_template = "acl/index.html"
    base_route = "admin.acls"
    edit_route = "admin.edit_acl"

    @classmethod
    def get_extra_context(cls, object_id: int):
        dpl = DataPersistenceLayer()
        return {"roles": [p.model_dump() for p in dpl.get_objects(Role)]}

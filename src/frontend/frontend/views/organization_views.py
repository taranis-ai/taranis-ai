from models.admin import Organization
from frontend.views.base_view import BaseView
from frontend.views.admin_mixin import AdminMixin


class OrganizationView(AdminMixin, BaseView):
    model = Organization
    icon = "building-office"
    _index = 30

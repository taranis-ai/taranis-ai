from models.admin import Organization

from frontend.views.admin_views.admin_mixin import AdminMixin
from frontend.views.base_view import BaseView


class OrganizationView(AdminMixin, BaseView):
    model = Organization
    icon = "building-office"
    _index = 30

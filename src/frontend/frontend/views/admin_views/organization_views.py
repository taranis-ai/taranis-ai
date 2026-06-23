from models.admin import Organization

from frontend.views.admin_views.admin_base_view import AdminBaseView


class OrganizationView(AdminBaseView):
    model = Organization
    icon = "building-office"
    _index = 30

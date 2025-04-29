from models.admin import Organization
from frontend.views.base_view import BaseView


class OrganizationView(BaseView):
    model = Organization

from frontend.models import Organization
from frontend.views.base_view import BaseView


class OrganizationView(BaseView):
    model = Organization

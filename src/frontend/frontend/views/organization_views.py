from frontend.models import Organization
from frontend.views.base_view import BaseView


class OrganizationView(BaseView):
    model = Organization
    htmx_list_template = "organization/organizations_table.html"
    htmx_update_template = "organization/organization_form.html"
    default_template = "organization/index.html"
    base_route = "admin.organizations"
    edit_route = "admin.edit_organization"

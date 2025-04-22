from flask import render_template
from frontend.models import Organization
from frontend.views.base_view import BaseView


class OrganizationView(BaseView):
    model = Organization
    htmx_list_template = "organization/organizations_table.html"
    htmx_update_template = "organization/organization_form.html"
    default_template = "organization/index.html"
    base_route = "admin.organizations"
    edit_route = "admin.edit_organization"

    @classmethod
    def get_extra_context(cls, object_id: int):
        return {}

    @classmethod
    def edit_organization_view(cls, organization_id: int = 0):
        template = OrganizationView.get_update_template()
        context = OrganizationView.get_update_context(organization_id)
        return render_template(template, **context)

    @classmethod
    def update_organization_view(cls, organization_id: int = 0):
        return OrganizationView.update_view(organization_id)

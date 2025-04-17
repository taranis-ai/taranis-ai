from flask import render_template
from frontend.models import Organization
from frontend.views.base_view import BaseView


class OrganizationView(BaseView):
    model = Organization
    id_key = "organization"
    htmx_template = "organization/organization_form.html"
    default_template = "organization/index.html"
    base_route = "admin.organizations"
    edit_route = "admin.edit_organization"

    @classmethod
    def get_extra_context(cls, object_id: int):
        return {}


def edit_organization_view(organization_id: int = 0):
    template = OrganizationView.select_template()
    context = OrganizationView.get_context(organization_id)
    return render_template(template, **context)


def update_organization_view(organization_id: int = 0):
    return OrganizationView.update_view(organization_id)

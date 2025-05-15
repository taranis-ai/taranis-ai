from frontend.views.base_view import BaseView
from models.admin import Template


class TemplateView(BaseView):
    model = Template

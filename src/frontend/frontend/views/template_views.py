from frontend.views.base_view import BaseView
from models.admin import Template


class TemplateView(BaseView):
    model = Template
    icon = "document-text"

    @classmethod
    def model_plural_name(cls) -> str:
        return "template_data"

    @classmethod
    def get_columns(cls):
        return [{"title": "name", "field": "id", "sortable": True, "renderer": None}]

from frontend.views.base_view import BaseView
from models.admin import Template


class TemplateView(BaseView):
    model = Template
    icon = "document-text"
    _index = 160

    @classmethod
    def model_plural_name(cls) -> str:
        return "template_data"

    @classmethod
    def get_columns(cls):
        return [{"title": "name", "field": "id", "sortable": True, "renderer": None}]

    @classmethod
    def _get_object_key(cls) -> str:
        return f"{cls.model_name().lower()}"

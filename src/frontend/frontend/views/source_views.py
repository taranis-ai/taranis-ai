from models.admin import OSINTSource
from frontend.views.base_view import BaseView


class SourceView(BaseView):
    model = OSINTSource
    icon = "book-open"
    _index = 63

from models.admin import WordList
from frontend.views.base_view import BaseView


class WordListView(BaseView):
    model = WordList
    icon = "chat-bubble-bottom-center-text"
    _index = 170

    form_fields = {
        "name": {},
        "description": {},
        "link": {},
        "include": {},
        "exclude": {},
        "tagging": {},
    }

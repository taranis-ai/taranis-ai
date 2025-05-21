from models.admin import WordList
from frontend.views.base_view import BaseView


class WordListView(BaseView):
    model = WordList
    icon = "chat-bubble-bottom-center-text"
    _index = 170

from frontend.views.base_view import BaseView
from models.admin import Bot


class BotView(BaseView):
    model = Bot
    icon = "calculator"
    _index = 110

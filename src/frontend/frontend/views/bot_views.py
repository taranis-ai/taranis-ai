from frontend.views.base_view import BaseView
from models.admin import Bot


class BotView(BaseView):
    model = Bot

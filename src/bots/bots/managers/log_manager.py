import os

from bots.config import settings
from shared.log import TaranisLogger


class Logger(TaranisLogger):
    def log_bot_activity(self, bot_type, bot, message):
        log_text = f"BOT {bot_type}/{bot}: {message}"
        self.log_info(log_text)


gunicorn = "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")
logger = Logger(module=settings.MODULE_ID, colored=settings.COLORED_LOGS, debug=settings.DEBUG, gunicorn=gunicorn, syslog_address=None)

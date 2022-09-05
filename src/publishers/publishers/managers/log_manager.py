import os

from publishers.config import Config
from shared.log import TaranisLogger


class Logger(TaranisLogger):
    def log_publisher_activity(self, publisher_type, message):
        log_text = f"[{publisher_type}]: {message}"
        self.log_info(log_text)


gunicorn = "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")
logger = Logger(module=Config.MODULE_ID, colored=Config.COLORED_LOGS, debug=Config.DEBUG, gunicorn=gunicorn, syslog_address=None)

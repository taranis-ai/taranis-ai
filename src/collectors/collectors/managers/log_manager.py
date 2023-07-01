import os
from collectors.config import Config
from shared.log import TaranisLogger


class Logger(TaranisLogger):
    def log_collector_activity(self, collector_type, collector, message):
        log_text = f"COLLECTOR {collector_type}/{collector}: {message}"
        self.log_info(log_text)

    def collector_exception(self, source, message: str):
        logger.log_info(f"OSINTSource [{source['id']}/{source['name']}]: {message}")

gunicorn = "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")

logger = Logger(
    module=Config.MODULE_ID, colored=Config.COLORED_LOGS, debug=Config.DEBUG, gunicorn=gunicorn, syslog_address=None
)

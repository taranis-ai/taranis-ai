from collectors.config import Config
from shared.log import TaranisLogger


class Logger(TaranisLogger):
    def log_collector_activity(self, collector_type, collector, message):
        log_text = f"COLLECTOR {collector_type}/{collector}: {message}"
        self.log_info(log_text)


logger = Logger(
    module=Config.MODULE_ID, colored=Config.COLORED_LOGS, debug=Config.DEBUG, gunicorn=Config.GUNICORN, syslog_address=Config.SYSLOG_ADDRESS
)

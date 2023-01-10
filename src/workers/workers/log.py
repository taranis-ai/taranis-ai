from workers.config import get_settings
from shared.log import TaranisLogger


class Logger(TaranisLogger):
    def log_worker_activity(self, worker_type, bot, message):
        log_text = f"WORKER {worker_type}/{bot}: {message}"
        self.log_info(log_text)


config = get_settings()
logger = Logger(module=config.MODULE_ID, colored=config.COLORED_LOGS, debug=config.DEBUG, gunicorn="", syslog_address=None)

import logging
import logging.handlers
import socket
import sys
import traceback

from worker.config import Config


class TaranisLogger:
    def __init__(self, module: str, debug: bool, colored: bool, gunicorn: bool, syslog_address: tuple[str, int] | str | None):
        self.module = module
        stream_handler = logging.StreamHandler(stream=sys.stdout)
        if colored:
            stream_handler.setFormatter(TaranisLogFormatter(module))
        else:
            stream_handler.setFormatter(logging.Formatter(f"[%(asctime)s] [{module}] [%(levelname)s] - %(message)s"))
        sys_log_handler = None
        if syslog_address:
            try:
                sys_log_handler = logging.handlers.SysLogHandler(address=syslog_address, socktype=socket.SOCK_STREAM)
            except Exception:
                print("Unable to connect to syslog server!")

        lloggers = [logging.getLogger()]

        if gunicorn:
            lloggers = [logging.getLogger("gunicorn.error")]

        for llogger in lloggers:
            llogger.handlers.clear()
            llogger.setLevel(logging.INFO)

            if debug:
                llogger.setLevel(logging.DEBUG)

            if sys_log_handler:
                llogger.addHandler(sys_log_handler)

            llogger.addHandler(stream_handler)

        self.logger = lloggers[0]

    def debug(self, message):
        self.logger.debug(message)

    def exception(self, message=None):
        if message:
            self.logger.debug(message)
        self.logger.debug(traceback.format_exc())

    def info(self, message):
        self.logger.info(message)

    def critical(self, message):
        self.logger.critical(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def get_stream_handler(self) -> logging.StreamHandler | None:
        for h in self.logger.handlers:
            if isinstance(h, logging.StreamHandler):
                return h


class TaranisLogFormatter(logging.Formatter):
    def __init__(self, module, custom_prefix: str | None = None):
        grey = "\x1b[38;20m"
        blue = "\x1b[1;36m"
        yellow = "\x1b[33;20m"
        red = "\x1b[31;20m"
        bold_red = "\x1b[31;1m"
        reset = "\x1b[0m"
        self.module = module
        self.format_string = f"[%(asctime)s] [{module}] [%(levelname)s]"
        if custom_prefix:
            self.format_string += f" [{custom_prefix}]"
        self.format_string += " - %(message)s"
        self.datefmt = "%Y-%m-%d %H:%M:%S"
        self.FORMATS = {
            logging.DEBUG: grey + self.format_string + reset,
            logging.INFO: blue + self.format_string + reset,
            logging.WARNING: yellow + self.format_string + reset,
            logging.ERROR: red + self.format_string + reset,
            logging.CRITICAL: bold_red + self.format_string + reset,
        }

    def format(self, record: logging.LogRecord):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt=self.datefmt)
        return formatter.format(record)


class Logger(TaranisLogger):
    def log_worker_activity(self, worker_type, bot, message):
        log_text = f"WORKER {worker_type}/{bot}: {message}"
        self.info(log_text)


# Setup logging configuration
def setup_logging():
    """Setup logging for RQ workers."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if Config.DEBUG:
        root_logger.setLevel(logging.DEBUG)


logger = Logger(module=Config.MODULE_ID, colored=Config.COLORED_LOGS, debug=Config.DEBUG, gunicorn=False, syslog_address=None)

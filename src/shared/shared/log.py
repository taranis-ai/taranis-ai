import logging.handlers
import sys
import socket
import logging
import traceback
from typing import Optional


class TaranisLogger:
    def __init__(self, module: str, debug: bool, colored: bool, gunicorn: bool, syslog_address: Optional[tuple]):
        self.module = module
        stream_handler = logging.StreamHandler(stream=sys.stdout)
        if colored:
            stream_handler.setFormatter(TaranisLogFormatter(module))
        else:
            stream_handler.setFormatter(logging.Formatter(f"[{module}] [%(levelname)s] - %(message)s"))
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

    def log_debug(self, message):
        self.logger.debug(message)

    def debug(self, message):
        self.logger.debug(message)

    def log_debug_trace(self, message=None):
        if message:
            self.logger.debug(message)
        self.logger.debug(traceback.format_exc())

    def exception(self, message=None):
        self.log_debug_trace(message)

    def log_info(self, message):
        self.logger.info(message)

    def info(self, message):
        self.logger.info(message)

    def log_critical(self, message):
        self.logger.critical(message)

    def critical(self, message):
        self.logger.critical(message)

    def log_warning(self, message):
        self.logger.warning(message)

    def warning(self, message):
        self.logger.warning(message)

    def log_error(self, message):
        self.logger.error(message)

    def error(self, message):
        self.logger.error(message)


class TaranisLogFormatter(logging.Formatter):
    def __init__(self, module):
        grey = "\x1b[38;20m"
        blue = "\x1b[1;36m"
        yellow = "\x1b[33;20m"
        red = "\x1b[31;20m"
        bold_red = "\x1b[31;1m"
        reset = "\x1b[0m"
        self.module = module
        self.format_string = f"[{self.module}] [%(levelname)s] - %(message)s"
        self.FORMATS = {
            logging.DEBUG: grey + self.format_string + reset,
            logging.INFO: blue + self.format_string + reset,
            logging.WARNING: yellow + self.format_string + reset,
            logging.ERROR: red + self.format_string + reset,
            logging.CRITICAL: bold_red + self.format_string + reset,
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

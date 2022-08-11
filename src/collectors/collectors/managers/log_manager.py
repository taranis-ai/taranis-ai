import os
import socket
import logging
import logging.handlers
import traceback
import sys

from collectors.config import Config


class Logger:
    module_id = Config.MODULE_ID

    def __init__(self):
        stream_handler = logging.StreamHandler(stream=sys.stdout)
        sys_log_handler = None
        if "SYSLOG_ADDRESS" in os.environ:
            try:
                syslog_address = os.getenv("SYSLOG_ADDRESS")
                syslog_port = int(os.getenv("SYSLOG_PORT"), 514)
                sys_log_handler = logging.handlers.SysLogHandler(address=(syslog_address, syslog_port), socktype=socket.SOCK_STREAM)
            except Exception as ex:
                self.log_debug("Unable to connect to syslog server!")
                self.log_debug(ex)

        lloggers = [logging.getLogger()]

        if "gunicorn" in os.environ.get("SERVER_SOFTWARE", ""):
            lloggers = [logging.getLogger("gunicorn.error")]

        if os.environ.get("LOG_SQLALCHEMY", False):
            lloggers.append(logging.getLogger("sqlalchemy"))

        for llogger in lloggers:
            llogger.setLevel(logging.INFO)

            if os.environ.get("DEBUG", "false").lower() == "true":
                llogger.setLevel(logging.DEBUG)

            if sys_log_handler:
                llogger.addHandler(sys_log_handler)

            llogger.addHandler(stream_handler)

        self.logger = lloggers[0]

    def log_debug(self, message):
        formatted_message = f"[{self.module_id}] {message}"
        self.logger.debug(formatted_message)

    def log_debug_trace(self, message=None):
        formatted_message = f"[{self.module_id}] {message}"
        formatted_message_exc = f"[{self.module_id}] {traceback.format_exc()}"

        if message:
            self.logger.debug(formatted_message)
        self.logger.debug(formatted_message_exc)

    def log_info(self, message):
        formatted_message = f"[{self.module_id}] {message}"
        self.logger.info(formatted_message)

    def log_critical(self, message):
        formatted_message = f"[{self.module_id}] {message}"
        self.logger.critical(formatted_message)

    def log_system_activity(self, module, message):
        self.log_info(f"[{module}] {message}")

    def log_collector_activity(self, collector_type, collector, message):
        log_text = f"COLLECTOR {collector_type}/{collector}: {message}"
        self.log_info(log_text)


logger = Logger()

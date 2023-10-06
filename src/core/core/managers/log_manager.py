from flask import request
import re
import os
import logging.handlers
import sys
import socket
import logging
import traceback
from typing import Optional

from core.config import Config


class TaranisLogger:
    def __init__(self, module: str, debug: bool, colored: bool, gunicorn: bool, syslog_address: Optional[tuple[str, int]]):
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


class Logger(TaranisLogger):
    def resolve_ip_address(self):
        headers_list = request.headers.getlist("X-Forwarded-For")
        return headers_list[0] if headers_list else request.remote_addr

    def resolve_method(self):
        return request.method

    def resolve_resource(self):
        fp_len = len(request.full_path)
        return request.full_path[: fp_len - 1] if request.full_path[fp_len - 1] == "?" else request.full_path

    def resolve_data(self):
        if "application/json" not in request.headers.get("Content-Type", ""):
            return ""
        if request.data is None:
            return ""

        return str(request.data)[:4096].replace("\\r", "").replace("\\n", "").replace(" ", "")[2:-1]

    def generate_escaped_data(self):
        data = self.resolve_data()
        return re.escape(data)[:4096]

    def rollback_and_store_to_db(self, log_data):
        from core.managers.db_manager import db

        db.session.rollback()

        # from core.model.log_record import LogRecord
        # LogRecord.store(log_data)

    def store_data_error_activity(self, user, activity_detail):
        self.store_user_auth_error_activity(user, activity_detail, "Data Error: (%s)")

    def store_data_error_activity_no_user(self, activity_detail):
        log_data = {
            "ip_address": self.resolve_ip_address(),
            "user": None,
            "system_id": None,
            "system_name": None,
            "module_id": self.module,
            "activity_type": None,
            "activity_resource": self.resolve_resource(),
            "activity_detail": activity_detail,
            "activity_method": self.resolve_method(),
            "activity_data": self.resolve_data(),
        }

        self.rollback_and_store_to_db(log_data)
        self.logger.error("Public Access Data Error: (%s)", log_data)

    def store_auth_error_activity(self, activity_detail):
        log_data = {
            "ip_address": self.resolve_ip_address(),
            "user": None,
            "system_id": None,
            "system_name": None,
            "module_id": self.module,
            "activity_type": None,
            "activity_resource": self.resolve_resource(),
            "activity_detail": activity_detail,
            "activity_method": self.resolve_method(),
            "activity_data": self.resolve_data(),
        }

        self.rollback_and_store_to_db(log_data)
        self.logger.error("Auth Error: (%s)", log_data)

    def store_user_auth_error_activity(self, user, activity_detail, message):
        log_data = {
            "ip_address": self.resolve_ip_address(),
            "user": user,
            "system_id": None,
            "system_name": None,
            "module_id": self.module,
            "activity_type": None,
            "activity_resource": self.resolve_resource(),
            "activity_detail": activity_detail,
            "activity_method": self.resolve_method(),
            "activity_data": self.resolve_data(),
        }

        self.rollback_and_store_to_db(log_data)
        self.logger.error(message, log_data)

    def store_system_error_activity(self, system_id, system_name, activity_type, activity_detail):
        log_data = {
            "ip_address": self.resolve_ip_address(),
            "user": None,
            "system_id": system_id,
            "system_name": system_name,
            "module_id": self.module,
            "activity_type": activity_type,
            "activity_resource": self.resolve_resource(),
            "activity_detail": activity_detail,
            "activity_method": self.resolve_method(),
            "activity_data": self.resolve_data(),
        }

        self.rollback_and_store_to_db(log_data)
        self.logger.error("System Critical: (%s)", log_data)

    def store_system_activity(self, system_id, system_name, activity_type, activity_detail):
        pass

    def store_activity(self, activity_type, activity_detail):
        pass

    def store_user_activity(self, user, activity_type, activity_detail):
        self.logger.debug(f"User: {user.name} activity_type: {activity_type} activity_detail: {activity_detail}")


gunicorn = "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")
logger = Logger(module=Config.MODULE_ID, colored=Config.COLORED_LOGS, debug=Config.DEBUG, gunicorn=gunicorn, syslog_address=None)

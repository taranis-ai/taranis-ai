import json
import logging
import logging.handlers
import socket
import sys
from typing import Any, Optional

from flask import request

from core.config import Config


_SENSITIVE_JSON_FIELDS = {
    "password",
    "old_password",
    "new_password",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "secret",
}


def _redact_sensitive_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "***" if str(key).lower() in _SENSITIVE_JSON_FIELDS else _redact_sensitive_json(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_redact_sensitive_json(item) for item in value]
    return value


class TaranisLogger:
    def __init__(self, module: str, debug: bool, colored: bool, syslog_address: Optional[tuple[str, int]]):
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

        self.logger = logging.getLogger(module)
        self.logger.handlers.clear()
        self.logger.setLevel(logging.INFO)

        if debug:
            self.logger.setLevel(logging.DEBUG)

        if sys_log_handler:
            self.logger.addHandler(sys_log_handler)

        self.logger.addHandler(stream_handler)

    def debug(self, message, *args, **kwargs):
        self.logger.debug(message, *args, **kwargs)

    def exception(self, message=None, *args, **kwargs):
        self.logger.exception(message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        self.logger.info(message, *args, **kwargs)

    def critical(self, message, *args, **kwargs):
        self.logger.critical(message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        self.logger.warning(message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        self.logger.error(message, *args, **kwargs)


class TaranisLogFormatter(logging.Formatter):
    def __init__(self, module):
        grey = "\x1b[38;20m"
        blue = "\x1b[1;36m"
        yellow = "\x1b[33;20m"
        red = "\x1b[31;20m"
        bold_red = "\x1b[31;1m"
        reset = "\x1b[0m"
        self.format_string = f"[%(asctime)s] [{module}] [%(levelname)s] - %(message)s"
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

        if isinstance(json_data := request.get_json(silent=True), (dict, list)):
            if Config.DEBUG:
                return json.dumps(json_data, separators=(",", ":"), sort_keys=True)[:4096]
            return json.dumps(_redact_sensitive_json(json_data), separators=(",", ":"), sort_keys=True)[:4096]

        return str(request.data)[:4096].replace("\\r", "").replace("\\n", "").replace(" ", "")[2:-1]

    def rollback_and_store_to_db(self, log_data):
        from core.managers.db_manager import db

        db.session.rollback()

        # from core.model.log_record import LogRecord
        # LogRecord.store(log_data)

    def store_auth_error_activity(self, activity_detail):
        log_data = {
            "ip_address": self.resolve_ip_address(),
            "activity_resource": self.resolve_resource(),
            "activity_detail": activity_detail,
            "activity_method": self.resolve_method(),
            "activity_data": self.resolve_data(),
        }

        self.rollback_and_store_to_db(log_data)
        self.logger.error("Auth Error: (%s)", log_data)

    def store_user_activity(self, user, activity_type, activity_detail):
        self.logger.debug(f"User: {user.name} activity_type: {activity_type} activity_detail: {activity_detail}")


logger = Logger(module=Config.MODULE_ID, colored=Config.COLORED_LOGS, debug=Config.DEBUG, syslog_address=None)

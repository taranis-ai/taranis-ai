import logging.handlers
import os
import re
import sys
import socket
import logging
import traceback
from flask import request

from core.config import Config


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

    def resolve_ip_address(self):
        headers_list = request.headers.getlist("X-Forwarded-For")
        return headers_list[0] if headers_list else request.remote_addr

    def resolve_method(self):
        return request.method

    def resolve_resource(self):
        fp_len = len(request.full_path)
        if request.full_path[fp_len - 1] == "?":
            return request.full_path[: fp_len - 1]
        else:
            return request.full_path

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

    def store_access_error_activity(self, user, activity_detail):
        log_data = {
            "ip_address": self.resolve_ip_address(),
            "user_id": user.id,
            "user_name": user.name,
            "system_id": None,
            "system_name": None,
            "module_id": self.module_id,
            "activity_type": None,
            "activity_resource": self.resolve_resource(),
            "activity_detail": activity_detail,
            "activity_method": self.resolve_method(),
            "activity_data": self.resolve_data(),
        }

        self.rollback_and_store_to_db(log_data)
        self.logger.critical("TARANIS NG Access Error: (%s)", log_data)

    def store_data_error_activity(self, user, activity_detail):
        log_data = {
            "ip_address": self.resolve_ip_address(),
            "user_id": user.id,
            "user_name": user.name,
            "system_id": None,
            "system_name": None,
            "module_id": self.module_id,
            "activity_type": None,
            "activity_resource": self.resolve_resource(),
            "activity_detail": activity_detail,
            "activity_method": self.resolve_method(),
            "activity_data": self.resolve_data(),
        }

        self.rollback_and_store_to_db(log_data)
        self.logger.critical("TARANIS NG Data Error: (%s)", log_data)

    def store_data_error_activity_no_user(self, activity_detail):
        log_data = {
            "ip_address": self.resolve_ip_address(),
            "user_id": None,
            "user_name": None,
            "system_id": None,
            "system_name": None,
            "module_id": self.module_id,
            "activity_type": None,
            "activity_resource": self.resolve_resource(),
            "activity_detail": activity_detail,
            "activity_method": self.resolve_method(),
            "activity_data": self.resolve_data(),
        }

        self.rollback_and_store_to_db(log_data)
        self.logger.critical("TARANIS NG Public Access Data Error: (%s)", log_data)

    def store_auth_error_activity(self, activity_detail):
        log_data = {
            "ip_address": self.resolve_ip_address(),
            "user_id": None,
            "user_name": None,
            "system_id": None,
            "system_name": None,
            "module_id": self.module_id,
            "activity_type": None,
            "activity_resource": self.resolve_resource(),
            "activity_detail": activity_detail,
            "activity_method": self.resolve_method(),
            "activity_data": self.resolve_data(),
        }

        self.rollback_and_store_to_db(log_data)
        self.logger.critical("TARANIS NG Auth Error: (%s)", log_data)

    def store_user_auth_error_activity(self, user, activity_detail):
        log_data = {
            "ip_address": self.resolve_ip_address(),
            "user_id": user.id,
            "user_name": user.name,
            "system_id": None,
            "system_name": None,
            "module_id": self.module_id,
            "activity_type": None,
            "activity_resource": self.resolve_resource(),
            "activity_detail": activity_detail,
            "activity_method": self.resolve_method(),
            "activity_data": self.resolve_data(),
        }

        self.rollback_and_store_to_db(log_data)
        self.logger.critical("TARANIS NG Auth Critical: (%s)", log_data)

    def store_system_error_activity(self, system_id, system_name, activity_type, activity_detail):
        log_data = {
            "ip_address": self.resolve_ip_address(),
            "user_id": None,
            "user_name": None,
            "system_id": system_id,
            "system_name": system_name,
            "module_id": self.module_id,
            "activity_type": activity_type,
            "activity_resource": self.resolve_resource(),
            "activity_detail": activity_detail,
            "activity_method": self.resolve_method(),
            "activity_data": self.resolve_data(),
        }

        self.rollback_and_store_to_db(log_data)
        self.logger.critical("TARANIS NG System Critical: (%s)", log_data)

    def store_system_activity(self, system_id, system_name, activity_type, activity_detail):
        pass

    def store_activity(self, activity_type, activity_detail):
        pass

    def store_user_activity(self, user, activity_type, activity_detail):
        self.logger.debug(f"User: {user.name} activity_type: {activity_type} activity_detail: {activity_detail}")


logger = Logger()

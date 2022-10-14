from flask import request
import re
import os

from core.config import Config
from shared.log import TaranisLogger


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

    def store_access_error_activity(self, user, activity_detail):
        self.store_user_auth_error_activity(user, activity_detail, "TARANIS NG Access Error: (%s)")

    def store_data_error_activity(self, user, activity_detail):
        self.store_user_auth_error_activity(user, activity_detail, "TARANIS NG Data Error: (%s)")

    def store_data_error_activity_no_user(self, activity_detail):
        log_data = {
            "ip_address": self.resolve_ip_address(),
            "user_id": None,
            "user_name": None,
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
        self.logger.critical("TARANIS NG Public Access Data Error: (%s)", log_data)

    def store_auth_error_activity(self, activity_detail):
        log_data = {
            "ip_address": self.resolve_ip_address(),
            "user_id": None,
            "user_name": None,
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
        self.logger.critical("TARANIS NG Auth Error: (%s)", log_data)

    def store_user_auth_error_activity(self, user, activity_detail, message):
        log_data = {
            "ip_address": self.resolve_ip_address(),
            "user_id": user.id,
            "user_name": user.name,
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
        self.logger.critical(message, log_data)

    def store_system_error_activity(self, system_id, system_name, activity_type, activity_detail):
        log_data = {
            "ip_address": self.resolve_ip_address(),
            "user_id": None,
            "user_name": None,
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
        self.logger.critical("TARANIS NG System Critical: (%s)", log_data)

    def store_system_activity(self, system_id, system_name, activity_type, activity_detail):
        pass

    def store_activity(self, activity_type, activity_detail):
        pass

    def store_user_activity(self, user, activity_type, activity_detail):
        self.logger.debug(f"User: {user.name} activity_type: {activity_type} activity_detail: {activity_detail}")


gunicorn = "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")
logger = Logger(module=Config.MODULE_ID, colored=Config.COLORED_LOGS, debug=Config.DEBUG, gunicorn=gunicorn, syslog_address=None)

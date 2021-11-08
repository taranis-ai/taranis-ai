import logging.handlers
import os
import re
import socket
from logging import getLogger
import traceback
from flask import request

from managers.db_manager import db
from model.log_record import LogRecord

# setup Flask logger
gunicorn_logger = getLogger('gunicorn.error')
gunicorn_logger.setLevel(logging.INFO)

# setup syslog logger
sys_logger = logging.getLogger('SysLogger')
sys_logger.setLevel(logging.INFO)

if "MODULE_ID" in os.environ:
    module_id = os.environ.get("MODULE_ID")
else:
    module_id = None

# increase logging level
if "DEBUG" in os.environ and os.environ.get("DEBUG").lower() == "true":
    gunicorn_logger.setLevel(logging.DEBUG)
    sys_logger.setLevel(logging.DEBUG)


# send a debug message
def log_debug(message):
    formatted_message = "[{}] {}".format(module_id,message)
    gunicorn_logger.debug(formatted_message)
    if sys_logger:
        sys_logger.debug(formatted_message)

# send a debug message
def log_debug_trace(message = None):
    formatted_message1 = "[{}] {}".format(module_id,message)
    formatted_message2 = "[{}] {}".format(module_id,traceback.format_exc())

    if message:
        gunicorn_logger.debug(formatted_message1)
    gunicorn_logger.debug(formatted_message2)
    if sys_logger:
        if message:
            sys_logger.debug(formatted_message1)
        sys_logger.debug(formatted_message2)

# send an info message
def log_info(message):
    formatted_message = "[{}] {}".format(module_id,message)
    gunicorn_logger.info(formatted_message)
    if sys_logger:
        sys_logger.info(formatted_message)

# send a critical message
def log_critical(message):
    formatted_message = "[{}] {}".format(module_id,message)
    gunicorn_logger.critical(formatted_message)
    if sys_logger:
        sys_logger.critical(formatted_message)

# try to connect syslog logger
if "SYSLOG_URL" in os.environ and "SYSLOG_PORT" in os.environ:
    try:
        sys_log_handler = logging.handlers.SysLogHandler(
            address=(os.environ["SYSLOG_URL"], int(os.environ["SYSLOG_PORT"])),
            socktype=socket.SOCK_STREAM)
        sys_logger.addHandler(sys_log_handler)
    except Exception as ex:
        sys_logger = None
        log_debug("Unable to connect to syslog server!")
        log_debug(ex)
elif "SYSLOG_ADDRESS" in os.environ:
    try:
        sys_log_handler = logging.handlers.SysLogHandler(address=os.environ["SYSLOG_ADDRESS"])
        sys_logger.addHandler(sys_log_handler)
    except Exception as ex:
        sys_logger = None
        log_debug("Unable to connect to syslog server!")
        log_debug(ex)


def resolve_ip_address():
    headers_list = request.headers.getlist("X-Forwarded-For")
    ip_address = headers_list[0] if headers_list else request.remote_addr
    return ip_address


def resolve_method():
    return request.method


def resolve_resource():
    fp_len = len(request.full_path)
    if request.full_path[fp_len - 1] == '?':
        return request.full_path[:fp_len - 1]
    else:
        return request.full_path


def resolve_data():
    if "Content-Type" in request.headers and "application/json" in request.headers["Content-Type"]:
        if request.data is not None:
            return str(request.data)[:4096].replace("\\r", "").replace("\\n", "").replace(" ", "")[2:-1]

    return ""


def generate_escaped_data():
    data = resolve_data()
    return re.escape(data)[:4096]


def store_activity(activity_type, activity_detail):
    LogRecord.store(resolve_ip_address(), None, None, None, None, module_id, activity_type, resolve_resource(),
                    activity_detail, resolve_method(), resolve_data())


def store_user_activity(user, activity_type, activity_detail):
    LogRecord.store(resolve_ip_address(), user.id, user.name, None, None, module_id, activity_type, resolve_resource(),
                    activity_detail, resolve_method(), resolve_data())


def store_access_error_activity(user, activity_detail):
    ip = resolve_ip_address()
    log_text = "TARANIS NG Access Error (IP: {}, User ID: {}, User Name: {}, Method: {}, Resource: {}, Activity Detail: {}, Activity Data: {})".format(
        ip,
        user.id,
        user.name,
        resolve_method(),
        resolve_resource(),
        activity_detail,
        generate_escaped_data())

    if sys_logger is not None:
        try:
            sys_logger.critical(log_text)
        except Exception(ex):
            log_debug(ex)

    print(log_text)
    db.session.rollback()
    LogRecord.store(ip, user.id, user.name, None, None, module_id, "ACCESS_ERROR", resolve_resource(),
                    activity_detail, resolve_method(), resolve_data())


def store_data_error_activity(user, activity_detail):
    db.session.rollback()
    ip = resolve_ip_address()
    log_text = "TARANIS NG Data Error (IP: {}, User ID: {}, User Name: {}, Method: {}, Resource: {}, Activity Detail: {}, Activity Data: {})".format(
        ip,
        user.id,
        user.name,
        resolve_method(),
        resolve_resource(),
        activity_detail,
        generate_escaped_data())

    if sys_logger is not None:
        try:
            sys_logger.critical(log_text)
        except Exception(ex):
            log_debug(ex)

    print(log_text)
    LogRecord.store(ip, user.id, user.name, None, None, module_id, "DATA_ERROR", resolve_resource(),
                    activity_detail, resolve_method(), resolve_data())


def store_data_error_activity_no_user(activity_detail):
    db.session.rollback()
    ip = resolve_ip_address()
    log_text = "TARANIS NG Public Access Data Error (IP: {}, Method: {}, Resource: {}, Activity Detail: {}, Activity Data: {})".format(
        ip,
        resolve_method(),
        resolve_resource(),
        activity_detail,
        generate_escaped_data())

    if sys_logger is not None:
        try:
            sys_logger.critical(log_text)
        except Exception(ex):
            log_debug(ex)

    print(log_text)
    LogRecord.store(ip, None, None, None, None, module_id, "PUBLIC_ACCESS_DATA_ERROR", resolve_resource(),
                    activity_detail, resolve_method(), resolve_data())


def store_auth_error_activity(activity_detail):
    db.session.rollback()
    log_text = "TARANIS NG Auth Error (Method: {}, Resource: {}, Activity Detail: {}, Activity Data: {})".format(
        resolve_method(),
        resolve_resource(),
        activity_detail,
        generate_escaped_data())

    if sys_logger is not None:
        try:
            sys_logger.error(log_text)
        except Exception(ex):
            log_debug(ex)

    print(log_text)
    LogRecord.store(resolve_ip_address(), None, None, None, None, module_id, "AUTH_ERROR", resolve_resource(),
                    activity_detail, resolve_method(), resolve_data())


def store_user_auth_error_activity(user, activity_detail):
    db.session.rollback()
    ip = resolve_ip_address()
    log_text = "TARANIS NG Auth Critical (IP: {}, User ID: {}, User Name: {}, Method: {}, Resource: {}, Activity Detail: {}, Activity Data: {})".format(
        ip,
        user.id,
        user.name,
        resolve_method(),
        resolve_resource(),
        activity_detail, generate_escaped_data())
    if sys_logger is not None:
        try:
            sys_logger.error(log_text)
        except Exception(ex):
            log_debug(ex)

    print(log_text)
    LogRecord.store(ip, user.id, user.name, None, None, module_id, "AUTH_ERROR", resolve_resource(),
                    activity_detail, resolve_method(), resolve_data())


def store_system_activity(system_id, system_name, activity_type, activity_detail):
    LogRecord.store(resolve_ip_address(), None, None, system_id, system_name, module_id, activity_type,
                    resolve_resource(), activity_detail, resolve_method(), resolve_data())


def store_system_error_activity(system_id, system_name, activity_type, activity_detail):
    db.session.rollback()
    ip = resolve_ip_address()
    log_text = "TARANIS NG System Critical (System ID: {}, System Name: {}, Activity Type: {}, Method: {}, Resource: {}, Activity Detail: {}, Activity Data: {})".format(
        ip,
        system_id,
        system_name,
        resolve_method(),
        resolve_resource(),
        activity_detail,
        generate_escaped_data())

    if sys_logger is not None:
        try:
            sys_logger.critical(log_text)
        except Exception(ex):
            log_debug(ex)

    print(log_text)
    LogRecord.store(resolve_ip_address(), None, None, system_id, system_name, module_id, activity_type,
                    resolve_resource(), activity_detail, resolve_method(), resolve_data())

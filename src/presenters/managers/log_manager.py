import os
import socket
import logging
import logging.handlers
import traceback

# setup Flask logger
gunicorn_logger = logging.getLogger('gunicorn.error')
gunicorn_logger.setLevel(logging.INFO)

# setup syslog logger
sys_logger = logging.getLogger('SysLogger')
sys_logger.setLevel(logging.INFO)

# custom module ID to append to log messages
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

def log_system_activity(module, message):
    log_info("[{}] {}".format(module, message))

def log_collector_activity(collector_type, collector, message):
    log_text = "COLLECTOR {}/{}: {}".format(
        collector_type,
        collector,
        message
    )
    log_info(log_text)
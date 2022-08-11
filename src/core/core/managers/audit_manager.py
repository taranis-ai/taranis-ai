from flask import request

from core.model.audit_record import AuditRecord


def resolve_ip_address():
    headers_list = request.headers.getlist("X-Forwarded-For")
    ip_address = headers_list[0] if headers_list else request.remote_addr
    return ip_address


def resolve_resource():
    fp_len = len(request.full_path)
    if request.full_path[fp_len - 1] == "?":
        return request.full_path[: fp_len - 1]
    else:
        return request.full_path.split("?")[0]


def store_activity(activity_type, activity_detail):
    AuditRecord.store(
        resolve_ip_address(),
        None,
        None,
        None,
        None,
        activity_type,
        resolve_resource(),
        activity_detail,
    )


def store_user_activity(user, activity_type, activity_detail):
    AuditRecord.store(
        resolve_ip_address(),
        user.id,
        user.name,
        None,
        None,
        activity_type,
        resolve_resource(),
        activity_detail,
    )


def store_auth_error_activity(activity_detail):
    AuditRecord.store(
        resolve_ip_address(),
        None,
        None,
        None,
        None,
        "AUTH_ERROR",
        resolve_resource(),
        activity_detail,
    )


def store_user_auth_error_activity(user, activity_detail):
    AuditRecord.store(
        resolve_ip_address(),
        user.id,
        user.name,
        None,
        None,
        "AUTH_ERROR",
        resolve_resource(),
        activity_detail,
    )


def store_system_activity(system_id, system_name, activity_type, activity_detail):
    AuditRecord.store(
        resolve_ip_address(),
        None,
        None,
        system_id,
        system_name,
        activity_type,
        resolve_resource(),
        activity_detail,
    )

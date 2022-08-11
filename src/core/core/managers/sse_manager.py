from flask import request, abort
from flask_sse import sse
from datetime import datetime
import os

from core.managers import auth_manager, bots_manager, time_manager, remote_manager
from core.model.remote import RemoteAccess


def use_sse():
    return os.getenv("REDIS_URL") is not None


def news_items_updated():
    if use_sse():
        sse.publish({}, type="news-items-updated")


def report_items_updated():
    if use_sse():
        sse.publish({}, type="report-items-updated")


def report_item_updated(data):
    if use_sse():
        sse.publish(data, type="report-item-updated")


def remote_access_disconnect(data):
    if use_sse():
        sse.publish(data, type="remote_access_disconnect", channel="remote")


def remote_access_news_items_updated(osint_source_ids):
    if use_sse():
        remote_access_event_ids = RemoteAccess.get_relevant_for_news_items(osint_source_ids)
        sse.publish(
            remote_access_event_ids,
            type="remote_access_news_items_updated",
            channel="remote",
        )


def remote_access_report_items_updated(report_item_type_id):
    if use_sse():
        remote_access_event_ids = RemoteAccess.get_relevant_for_report_item(report_item_type_id)
        sse.publish(
            remote_access_event_ids,
            type="remote_access_report_items_updated",
            channel="remote",
        )


report_item_locks = {}
report_item_locks_last_check_time = datetime.now()


@sse.before_request
def connect():
    if request.args.get("jwt") is not None:
        if auth_manager.decode_user_from_jwt(request.args.get("jwt")) is None:
            abort(403)
    elif request.args.get("api_key") is not None:
        if bots_manager.verify_api_key(request.args.get("api_key")) is False:
            abort(403)
    elif request.args.get("access_key") is not None and request.args.get("channel") is not None:
        if request.args.get("channel") == "remote":
            if remote_manager.verify_access_key(request.args.get("access_key")) is False:
                abort(403)
    else:
        abort(403)


def report_item_lock(report_item_id, field_id, user_id):
    if report_item_id in report_item_locks:
        report_item = report_item_locks[report_item_id]
    else:
        report_item = {}
        report_item_locks[report_item_id] = report_item

    if field_id not in report_item or report_item[field_id] is None:
        report_item[field_id] = {"user_id": user_id, "lock_time": datetime.now()}
        sse.publish(
            {
                "report_item_id": int(report_item_id),
                "field_id": field_id,
                "user_id": user_id,
            },
            type="report-item-locked",
        )


def report_item_unlock(report_item_id, field_id, user_id):
    if report_item_id in report_item_locks:
        report_item = report_item_locks[report_item_id]

        if field_id in report_item:
            report_item[field_id] = None

    sse.publish(
        {
            "report_item_id": int(report_item_id),
            "field_id": field_id,
            "user_id": user_id,
        },
        type="report-item-unlocked",
    )


def report_item_hold_lock(report_item_id, field_id, user_id):
    if report_item_id in report_item_locks:
        report_item = report_item_locks[report_item_id]
        if field_id in report_item and report_item[field_id] is not None:
            if report_item[field_id]["user_id"] == user_id:
                report_item[field_id]["lock_time"] = datetime.now()


def check_report_item_locks(app):
    global report_item_locks_last_check_time
    for key in report_item_locks:
        for field_key in report_item_locks[key]:
            if report_item_locks[key][field_key] is not None:
                if report_item_locks[key][field_key]["lock_time"] < report_item_locks_last_check_time:
                    report_item_locks[key][field_key] = None
                    with app.app_context():
                        sse.publish(
                            {
                                "report_item_id": int(key),
                                "field_id": field_key,
                                "user_id": -1,
                            },
                            type="report-item-unlocked",
                        )

    report_item_locks_last_check_time = datetime.now()


def initialize(app):
    time_manager.schedule_job_minutes(1, check_report_item_locks, app)

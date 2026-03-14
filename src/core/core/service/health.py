from typing import Literal

from celery.exceptions import CeleryError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from core.managers import queue_manager
from core.managers.db_manager import db


HealthStatus = Literal["up", "down", "n/a"]


def get_health_response() -> tuple[dict[str, bool | dict[str, HealthStatus]], int]:
    services: dict[str, HealthStatus] = {"database": check_database()}

    if broker_health_applicable():
        broker_status = check_broker()
        services["broker"] = broker_status
        services["workers"] = check_workers() if broker_status == "up" else "down"
    else:
        services["broker"] = "n/a"
        services["workers"] = "n/a"

    healthy = all(status != "down" for status in services.values())
    return {"healthy": healthy, "services": services}, 200 if healthy else 503


def broker_health_applicable() -> bool:
    broker_url = (queue_manager.queue_manager.celery.conf.broker_url or "").lower()
    return broker_url.startswith(("amqp://", "amqps://"))


def check_database() -> HealthStatus:
    try:
        db.session.execute(text("SELECT 1"))
        return "up"
    except SQLAlchemyError:
        return "down"


def check_broker() -> HealthStatus:
    try:
        with queue_manager.queue_manager.celery.connection() as conn:
            conn.ensure_connection(max_retries=1, timeout=1)
        return "up"
    except Exception:
        return "down"


def check_workers() -> HealthStatus:
    try:
        workers = queue_manager.queue_manager.celery.control.ping(timeout=1)
        return "up" if workers else "down"
    except (CeleryError, OSError):
        return "down"
    except Exception:
        return "down"

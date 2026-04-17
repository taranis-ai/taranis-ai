from typing import Literal

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from core.managers import queue_manager
from core.managers.db_manager import db


HealthStatus = Literal["up", "down", "n/a"]


def get_health_response() -> tuple[dict[str, bool | dict[str, HealthStatus]], int]:
    database_status = check_database()
    services: dict[str, HealthStatus] = {"database": database_status}
    services["seed_data"] = check_seed_data() if database_status == "up" else "down"

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
    qm = getattr(queue_manager, "queue_manager", None)
    return bool(qm and getattr(qm, "redis_url", None))


def check_database() -> HealthStatus:
    try:
        db.session.execute(text("SELECT 1"))
        return "up"
    except SQLAlchemyError:
        return "down"


def check_seed_data() -> HealthStatus:
    try:
        from core.model.osint_source import OSINTSource
        from core.model.product_type import ProductType

        manual_source_exists = OSINTSource.get("manual") is not None
        product_type_exists = ProductType.get_first(db.select(ProductType)) is not None
        return "up" if manual_source_exists and product_type_exists else "down"
    except SQLAlchemyError:
        return "down"
    except Exception:
        return "down"


def check_broker() -> HealthStatus:
    qm = getattr(queue_manager, "queue_manager", None)
    if not qm or not getattr(qm, "_redis", None):
        return "down"

    try:
        qm._redis.ping()
        return "up"
    except Exception:
        return "down"


def check_workers() -> HealthStatus:
    qm = getattr(queue_manager, "queue_manager", None)
    if not qm or not getattr(qm, "_redis", None):
        return "down"

    try:
        from rq.worker import Worker

        workers = Worker.all(connection=qm._redis)
        return "up" if workers else "down"
    except Exception:
        return "down"

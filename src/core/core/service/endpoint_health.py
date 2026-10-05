"""Probe configured bot services through the existing worker queue."""

import hashlib
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

from models.llm import LLM_BOT_FEATURES
from redis.exceptions import RedisError, WatchError
from rq import Retry

from core.config import Config
from core.log import logger
from core.managers import queue_manager
from core.service.cache_invalidation import invalidate_frontend_cache_on_success


if TYPE_CHECKING:
    from core.model.bot import Bot

RETRY_INTERVALS = [10, 30, 120, 300]
MESSAGES = {
    "pending": "Endpoint check pending.",
    "up": "Endpoint check succeeded.",
    "down": "Endpoint check failed. Check the URL, credentials, model, and service availability. Save to test again.",
    "n/a": "Endpoint checks require an enabled worker queue.",
}


def endpoint_config(kind: str, endpoint_id: str) -> dict | None:
    from core.model.settings import Settings

    if kind == "llm":
        return Settings.get_settings()["llm_endpoints"].get(endpoint_id)
    return None


def fingerprint(config: dict) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


def state_key(kind: str, endpoint_id: str) -> str:
    return f"taranis:endpoint-health:{kind}:{endpoint_id}"


def read_state(kind: str, endpoint_id: str) -> dict:
    qm = getattr(queue_manager, "queue_manager", None)
    if not Config.QUEUE_ENABLED or not qm or not qm.redis:
        return {}
    try:
        return json.loads(qm.redis.get(state_key(kind, endpoint_id)) or "{}")
    except (RedisError, ValueError):
        logger.exception("Failed to read endpoint health")
        return {}


def get_status(kind: str, endpoint_id: str, config: dict) -> dict:
    state = read_state(kind, endpoint_id)
    status = state.get("status", "pending") if state.get("fingerprint") == fingerprint(config) else "pending"
    if not Config.QUEUE_ENABLED:
        status = "n/a"
    return {"status": status, "message": MESSAGES[status], "checked_at": state.get("checked_at")}


def bot_status(bot: "Bot") -> dict | None:
    from core.model.settings import Settings

    if not bot.enabled:
        return None
    if bot.type.value in LLM_BOT_FEATURES:
        settings = Settings.get_settings()
        endpoint_id = bot.get_llm_endpoint_id(settings)
        if endpoint_id and (config := settings["llm_endpoints"].get(endpoint_id)):
            return get_status("llm", endpoint_id, config)
        return None
    return None


def schedule_check(kind: str, endpoint_id: str) -> None:
    qm = getattr(queue_manager, "queue_manager", None)
    if not Config.QUEUE_ENABLED or not qm or not qm.redis:
        return
    config = endpoint_config(kind, endpoint_id)
    invalidate_frontend_cache_on_success(200, models=("settings", "bot", "core_health", "dashboard", "admin_menu_badges"))
    try:
        if config is None:
            qm.redis.delete(state_key(kind, endpoint_id))
            return
        generation = uuid4().hex
        state = {"generation": generation, "fingerprint": fingerprint(config), "status": "pending"}
        qm.redis.set(state_key(kind, endpoint_id), json.dumps(state))
        job = qm.enqueue_task(
            "misc",
            "check_endpoint",
            kind,
            endpoint_id,
            generation,
            retry=Retry(max=len(RETRY_INTERVALS), interval=RETRY_INTERVALS),
            job_timeout=180,
        )
        if not job:
            record_result(kind, endpoint_id, generation, False)
    except RedisError:
        logger.exception("Failed to schedule endpoint check for %s %s", kind, endpoint_id)


def schedule_all() -> None:
    from core.model.settings import Settings

    for endpoint_id in Settings.get_settings()["llm_endpoints"]:
        schedule_check("llm", endpoint_id)


def record_result(kind: str, endpoint_id: str, generation: str, healthy: bool) -> bool:
    config = endpoint_config(kind, endpoint_id)
    if config is None:
        return False
    key = state_key(kind, endpoint_id)
    connection = queue_manager.queue_manager.redis
    if connection is None:
        return False
    try:
        with connection.pipeline() as pipe:
            pipe.watch(key)
            state = json.loads(pipe.get(key) or "{}")
            if state.get("generation") != generation or state.get("fingerprint") != fingerprint(config):
                return False
            state.update(status="up" if healthy else "down", checked_at=datetime.now(UTC).isoformat())
            pipe.multi()
            pipe.set(key, json.dumps(state))
            pipe.execute()
    except WatchError:
        return False  # A newer check owns this endpoint now.
    invalidate_frontend_cache_on_success(200, models=("settings", "bot", "core_health", "dashboard", "admin_menu_badges"))
    return True


def aggregate_status() -> Literal["up", "down", "n/a"]:
    from core.model.bot import Bot
    from core.model.settings import Settings

    statuses = [get_status("llm", key, config) for key, config in Settings.get_settings()["llm_endpoints"].items()]
    statuses.extend(status for bot in Bot.get_all_for_collector() if (status := bot_status(bot)))
    if any(item["status"] in {"down", "pending"} for item in statuses):
        return "down"
    return "up" if statuses else "n/a"

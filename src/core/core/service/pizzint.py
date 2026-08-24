from datetime import UTC, datetime

import requests
from models.dashboard import PizzintStatus
from redis.exceptions import RedisError

from core.log import logger
from core.managers import queue_manager


PIZZINT_API_URL = "https://www.pizzint.watch/api/dashboard-data"
PIZZINT_CACHE_KEY = "taranis:pizzint:dashboard"
PIZZINT_FRESH_KEY = f"{PIZZINT_CACHE_KEY}:fresh"
PIZZINT_REFRESH_KEY = f"{PIZZINT_CACHE_KEY}:refresh"
PIZZINT_FRESH_SECONDS = 600
PIZZINT_RETRY_SECONDS = 60
PIZZINT_STALE_SECONDS = 3600


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _load_status(key: str) -> PizzintStatus | None:
    redis = queue_manager.queue_manager.redis
    if redis is None:
        return None
    try:
        return PizzintStatus.model_validate_json(cached) if (cached := redis.get(key)) else None
    except (RedisError, TypeError, ValueError):
        logger.exception("Failed to read cached PizzINT dashboard data")
        return None


def _cache_status(status: PizzintStatus) -> None:
    redis = queue_manager.queue_manager.redis
    if redis is None:
        return
    try:
        payload = status.model_dump_json()
        redis.set(PIZZINT_CACHE_KEY, payload, ex=PIZZINT_STALE_SECONDS)
        redis.set(PIZZINT_FRESH_KEY, payload, ex=PIZZINT_FRESH_SECONDS)
    except (RedisError, TypeError, ValueError):
        logger.exception("Failed to cache PizzINT dashboard data")


def _begin_refresh() -> bool:
    redis = queue_manager.queue_manager.redis
    if redis is None:
        return True
    try:
        return bool(redis.set(PIZZINT_REFRESH_KEY, "1", ex=PIZZINT_RETRY_SECONDS, nx=True))
    except RedisError:
        logger.exception("Failed to reserve PizzINT dashboard refresh")
        return True


def _fetch_status(now: datetime) -> PizzintStatus:
    response = requests.get(
        PIZZINT_API_URL,
        params={"_t": int(now.timestamp() * 1000)},
        headers={"User-Agent": "TaranisAI/1.0"},
        timeout=5,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("success") is not True:
        raise ValueError("Invalid PizzINT response")
    details = payload["defcon_details"]

    return PizzintStatus(
        state=payload["data_freshness"],
        level=payload["defcon_level"],
        smoothed_index=details["smoothed_index"],
        observed_at=details["at_time"],
        fetched_at=now,
        reason=details["reason"],
    )


def get_pizzint_status() -> PizzintStatus:
    if fresh := _load_status(PIZZINT_FRESH_KEY):
        return fresh

    cached = _load_status(PIZZINT_CACHE_KEY)
    fallback = cached.model_copy(update={"state": "stale"}) if cached else PizzintStatus()
    if not _begin_refresh():
        return fallback

    try:
        status = _fetch_status(_utcnow())
    except Exception:
        logger.exception("Failed to retrieve PizzINT dashboard data")
        return fallback

    _cache_status(status)
    return status

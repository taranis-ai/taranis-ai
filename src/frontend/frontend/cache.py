from typing import TypeVar

from flask_caching import Cache
from models.base import TaranisBaseModel
from models.user import UserProfile

from frontend.config import Config
from frontend.log import logger


cache = Cache()
T = TypeVar("T", bound="TaranisBaseModel")


def add_user_to_cache(user: dict) -> UserProfile | None:
    try:
        user_object = UserProfile(**user)
        cache.set(key=f"user_cache_{user['username']}", value=user_object, timeout=Config.CACHE_DEFAULT_TIMEOUT)
        return user_object
    except Exception:
        logger.exception("Failed to add user to cache")
        return None


def get_user_from_cache(username: str) -> UserProfile | None:
    return cache.get(f"user_cache_{username}")


def remove_user_from_cache(username: str):
    cache.delete(f"user_cache_{username}")


def _get_cache_store():
    backend = getattr(cache, "cache", None)
    return getattr(backend, "_cache", None)


def get_cache_keys() -> list[str] | None:
    cache_store = _get_cache_store()
    if cache_store is None:
        return None

    try:
        return [str(key) for key in cache_store.keys()]
    except Exception:
        logger.exception("Failed to enumerate cache keys")
        return None


def list_cache_keys() -> list[str]:
    return get_cache_keys() or []


def matches_cache_key_suffix(key: object, suffix: str | None) -> bool:
    key_str = str(key)
    if suffix is None:
        return True
    if not suffix:
        return False

    normalized_suffix = suffix.replace("/", "_")
    return key_str.endswith(f"_{suffix}") or key_str.endswith(f"_{normalized_suffix}")


def invalidate_cache_keys(suffix: str | None = None) -> int:
    keys = get_cache_keys()
    if keys is None:
        cache.clear()
        logger.warning("Cache backend does not support key enumeration; cleared entire frontend cache")
        return -1

    invalidated = 0
    for key in keys:
        if matches_cache_key_suffix(key, suffix):
            cache.delete(key)
            invalidated += 1

    return invalidated


def get_cached_users() -> list[UserProfile]:
    prefix = "user_cache_"
    users = []
    for key in list_cache_keys():
        username = key.removeprefix(prefix)
        if username == key:
            continue
        if user := get_user_from_cache(username):
            users.append(user)
    return users


def add_model_to_cache(model: T, cache_key: str, user_id: int) -> T | None:
    try:
        cache.set(
            key=f"model_cache_{model._model_name}_{cache_key}_{user_id}",
            value=model,
            timeout=getattr(model, "_cache_timeout", Config.CACHE_DEFAULT_TIMEOUT),
        )
        return model
    except Exception:
        logger.exception("Failed to add model to cache")
        return None


def get_model_from_cache(model_name: str, cache_key: str, user_id: int) -> T | None:
    return cache.get(f"model_cache_{model_name}_{cache_key}_{user_id}")


def init(app):
    cache.init_app(app)

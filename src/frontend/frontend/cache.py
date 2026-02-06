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


def list_cache_keys():
    return cache.cache._cache.keys()


def get_cached_users() -> list[UserProfile]:
    prefix = "user_cache_"
    users = []
    for key in cache.cache._cache:
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

import json
from typing import Any, TypeVar

from flask import Flask
from models.base import TaranisBaseModel
from models.cache_contract import (
    CACHE_DEFAULT_TIMEOUT_DEFAULT,
    CACHE_KEY_PREFIX_DEFAULT,
    build_model_detail_key,
    build_model_list_key,
    build_namespace_pattern,
    build_user_profile_key,
    build_user_profile_pattern,
    get_secret_value,
    parse_user_profile_key,
)
from models.user import UserProfile
from redis import Redis

from frontend.log import logger


T = TypeVar("T", bound="TaranisBaseModel")


class FrontendCache:
    def __init__(self):
        self.client: Redis | None = None
        self.key_prefix = CACHE_KEY_PREFIX_DEFAULT
        self.default_timeout = CACHE_DEFAULT_TIMEOUT_DEFAULT

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def init(self, app: Flask):
        self.key_prefix = app.config["CACHE_KEY_PREFIX"]
        self.default_timeout = app.config["CACHE_DEFAULT_TIMEOUT"]

        if not app.config.get("CACHE_ENABLED", True):
            self.client = None
            logger.info("Frontend cache disabled")
            return

        redis_url = app.config.get("CACHE_REDIS_URL") or app.config.get("REDIS_URL")
        redis_password = get_secret_value(app.config.get("CACHE_REDIS_PASSWORD")) or get_secret_value(app.config.get("REDIS_PASSWORD"))
        if not redis_url:
            self.client = None
            logger.warning("Frontend cache disabled because no Redis URL is configured")
            return

        try:
            self.client = Redis.from_url(redis_url, password=redis_password, decode_responses=True)
            self.client.ping()
            logger.info("Frontend cache initialized with Redis backend")
        except Exception:
            self.client = None
            logger.exception("Failed to initialize frontend Redis cache; continuing without caching")

    def get(self, key: str) -> Any:
        if self.client is None:
            return None
        try:
            raw_value = self.client.get(key)
            if raw_value is None:
                return None
            return json.loads(raw_value)
        except Exception:
            logger.exception("Failed to read from cache")
            return None

    def set(self, key: str, value: Any, timeout: int | None = None) -> bool:
        if self.client is None:
            return False
        timeout = self.default_timeout if timeout is None else timeout
        try:
            serialized = json.dumps(value)
            return bool(self.client.set(name=key, value=serialized, ex=timeout))
        except Exception:
            logger.exception("Failed to write to cache")
            return False

    def delete(self, key: str) -> int:
        if self.client is None:
            return 0
        try:
            return int(self.client.delete(key))
        except Exception:
            logger.exception("Failed to delete cache key")
            return 0

    def clear(self) -> int:
        if self.client is None:
            return 0
        try:
            keys = self.scan_keys(self.namespace_pattern())
            deleted = 0
            for index in range(0, len(keys), 500):
                deleted += int(self.client.delete(*keys[index : index + 500]))
            return deleted
        except Exception:
            logger.exception("Failed to clear cache namespace")
            return 0

    def scan_keys(self, pattern: str) -> list[str]:
        if self.client is None:
            return []
        try:
            return sorted(str(key) for key in self.client.scan_iter(match=pattern, count=1000))
        except Exception:
            logger.exception("Failed to scan cache keys")
            return []

    def model_list_key(self, username: str, model_name: str, suffix: str | int | None) -> str:
        return build_model_list_key(self.key_prefix, username, model_name, suffix)

    def model_detail_key(self, username: str, model_name: str, object_id: str | int | None = None) -> str:
        return build_model_detail_key(self.key_prefix, username, model_name, object_id)

    def user_profile_key(self, username: str) -> str:
        return build_user_profile_key(self.key_prefix, username)

    def namespace_pattern(self) -> str:
        return build_namespace_pattern(self.key_prefix)


cache = FrontendCache()


def add_user_to_cache(user: dict) -> UserProfile | None:
    try:
        user_object = UserProfile(**user)
        cache.set(
            key=cache.user_profile_key(user_object.username),
            value=user_object.model_dump(mode="json"),
        )
        return user_object
    except Exception:
        logger.exception("Failed to add user to cache")
        return None


def get_user_from_cache(username: str) -> UserProfile | None:
    cached_user = cache.get(cache.user_profile_key(username))
    if cached_user is None:
        return None
    try:
        return UserProfile(**cached_user)
    except Exception:
        logger.exception("Failed to deserialize cached user")
        return None


def remove_user_from_cache(username: str):
    cache.delete(cache.user_profile_key(username))


def get_cache_keys() -> list[str]:
    return cache.scan_keys(cache.namespace_pattern())


def get_cached_users() -> list[UserProfile]:
    users: list[UserProfile] = []
    for key in cache.scan_keys(build_user_profile_pattern(cache.key_prefix)):
        if username := parse_user_profile_key(key):
            if user := get_user_from_cache(username):
                users.append(user)
    return users


def add_model_to_cache(model: T, cache_key: str, user_id: int | str) -> T | None:
    try:
        cache.set(
            key=cache.model_detail_key(str(user_id), model._model_name, cache_key),
            value=model.model_dump(mode="json"),
            timeout=getattr(model, "_cache_timeout", None),
        )
        return model
    except Exception:
        logger.exception("Failed to add model to cache")
        return None


def get_model_from_cache(model_name: str, cache_key: str, user_id: int | str) -> dict[str, Any] | None:
    return cache.get(cache.model_detail_key(str(user_id), model_name, cache_key))


def init(app):
    cache.init(app)

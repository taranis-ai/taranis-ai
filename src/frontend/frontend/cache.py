import json
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from flask import Flask, current_app, has_app_context
from models.base import TaranisBaseModel
from models.user import UserProfile
from redis import Redis

from frontend.config import Config
from frontend.log import logger


T = TypeVar("T", bound="TaranisBaseModel")

USER_PROFILE_CACHE_KIND = "profile"
LIST_CACHE_KIND = "list"
DETAIL_CACHE_KIND = "detail"
SINGLETON_CACHE_SUFFIX = "singleton"
DEFAULT_LIST_CACHE_SUFFIX = "default"


def _get_config_value(name: str, default: Any = None) -> Any:
    if has_app_context():
        return current_app.config.get(name, default)
    return getattr(Config, name, default)


def _get_secret_value(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "get_secret_value"):
        return value.get_secret_value()
    return str(value) or None


def normalize_cache_suffix(value: str | int | None) -> str:
    if value in (None, ""):
        return DEFAULT_LIST_CACHE_SUFFIX
    return str(value)


class CacheBackend(ABC):
    @property
    @abstractmethod
    def enabled(self) -> bool: ...

    @abstractmethod
    def get(self, key: str) -> Any: ...

    @abstractmethod
    def set(self, key: str, value: Any, timeout: int | None = None) -> bool: ...

    @abstractmethod
    def delete(self, key: str) -> int: ...

    @abstractmethod
    def clear(self) -> int: ...

    @abstractmethod
    def scan_keys(self, pattern: str) -> list[str]: ...


class NoOpCacheBackend(CacheBackend):
    @property
    def enabled(self) -> bool:
        return False

    def get(self, key: str) -> Any:
        return None

    def set(self, key: str, value: Any, timeout: int | None = None) -> bool:
        return False

    def delete(self, key: str) -> int:
        return 0

    def clear(self) -> int:
        return 0

    def scan_keys(self, pattern: str) -> list[str]:
        return []


class RedisCacheBackend(CacheBackend):
    def __init__(self, client: Redis, key_prefix: str):
        self.client = client
        self.key_prefix = key_prefix

    @property
    def enabled(self) -> bool:
        return True

    def get(self, key: str) -> Any:
        raw_value = self.client.get(key)
        if raw_value is None:
            return None
        return json.loads(raw_value)

    def set(self, key: str, value: Any, timeout: int | None = None) -> bool:
        serialized = json.dumps(value)
        if timeout is None:
            return bool(self.client.set(name=key, value=serialized))
        return bool(self.client.set(name=key, value=serialized, ex=timeout))

    def delete(self, key: str) -> int:
        return int(self.client.delete(key))

    def clear(self) -> int:
        keys = self.scan_keys(f"{self.key_prefix}:*")
        deleted = 0
        for index in range(0, len(keys), 500):
            deleted += int(self.client.delete(*keys[index : index + 500]))
        return deleted

    def scan_keys(self, pattern: str) -> list[str]:
        return sorted(str(key) for key in self.client.scan_iter(match=pattern, count=1000))


class FrontendCache:
    def __init__(self):
        self._backend: CacheBackend = NoOpCacheBackend()
        self.key_prefix = Config.CACHE_KEY_PREFIX
        self.default_timeout = Config.CACHE_DEFAULT_TIMEOUT

    @property
    def enabled(self) -> bool:
        return self._backend.enabled

    def init(self, app: Flask):
        self.key_prefix = app.config["CACHE_KEY_PREFIX"]
        self.default_timeout = app.config["CACHE_DEFAULT_TIMEOUT"]

        if not app.config.get("CACHE_ENABLED", True):
            self._backend = NoOpCacheBackend()
            logger.info("Frontend cache disabled")
            return

        redis_url = app.config.get("CACHE_REDIS_URL") or app.config.get("REDIS_URL")
        redis_password = _get_secret_value(app.config.get("CACHE_REDIS_PASSWORD")) or _get_secret_value(app.config.get("REDIS_PASSWORD"))
        if not redis_url:
            self._backend = NoOpCacheBackend()
            logger.warning("Frontend cache disabled because no Redis URL is configured")
            return

        try:
            client = Redis.from_url(redis_url, password=redis_password, decode_responses=True)
            client.ping()
            self._backend = RedisCacheBackend(client=client, key_prefix=self.key_prefix)
            logger.info("Frontend cache initialized with Redis backend")
        except Exception:
            self._backend = NoOpCacheBackend()
            logger.exception("Failed to initialize frontend Redis cache; continuing without caching")

    def get(self, key: str) -> Any:
        try:
            return self._backend.get(key)
        except Exception:
            logger.exception("Failed to read from cache")
            return None

    def set(self, key: str, value: Any, timeout: int | None = None) -> bool:
        timeout = timeout if timeout is not None else self.default_timeout
        try:
            return self._backend.set(key, value, timeout=timeout)
        except Exception:
            logger.exception("Failed to write to cache")
            return False

    def delete(self, key: str) -> int:
        try:
            return self._backend.delete(key)
        except Exception:
            logger.exception("Failed to delete cache key")
            return 0

    def clear(self) -> int:
        try:
            return self._backend.clear()
        except Exception:
            logger.exception("Failed to clear cache namespace")
            return 0

    def scan_keys(self, pattern: str) -> list[str]:
        try:
            return self._backend.scan_keys(pattern)
        except Exception:
            logger.exception("Failed to scan cache keys")
            return []

    def build_key(self, username: str, model_name: str, kind: str, suffix: str | int | None) -> str:
        normalized_suffix = normalize_cache_suffix(suffix)
        return f"{self.key_prefix}:user:{username}:model:{model_name}:{kind}:{normalized_suffix}"

    def model_list_key(self, username: str, model_name: str, suffix: str | int | None) -> str:
        return self.build_key(username, model_name, LIST_CACHE_KIND, suffix)

    def model_detail_key(self, username: str, model_name: str, object_id: str | int | None = None) -> str:
        return self.build_key(username, model_name, DETAIL_CACHE_KIND, object_id or SINGLETON_CACHE_SUFFIX)

    def user_profile_key(self, username: str) -> str:
        return self.build_key(username, UserProfile._model_name, USER_PROFILE_CACHE_KIND, "self")

    def namespace_pattern(self) -> str:
        return f"{self.key_prefix}:*"


cache = FrontendCache()


def add_user_to_cache(user: dict) -> UserProfile | None:
    try:
        user_object = UserProfile(**user)
        cache.set(
            key=cache.user_profile_key(user_object.username),
            value=user_object.model_dump(mode="json"),
            timeout=_get_config_value("CACHE_DEFAULT_TIMEOUT", Config.CACHE_DEFAULT_TIMEOUT),
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


def list_cache_keys() -> list[str]:
    return get_cache_keys()


def get_cached_users() -> list[UserProfile]:
    keys = cache.scan_keys(cache.namespace_pattern())
    users: list[UserProfile] = []
    for key in keys:
        parts = key.split(":")
        if len(parts) != 7:
            continue
        if parts[1] != "user" or parts[3] != "model":
            continue
        if parts[4] != UserProfile._model_name or parts[5] != USER_PROFILE_CACHE_KIND:
            continue
        username = parts[2]
        if user := get_user_from_cache(username):
            users.append(user)
    return users


def add_model_to_cache(model: T, cache_key: str, user_id: int | str) -> T | None:
    try:
        cache.set(
            key=cache.model_detail_key(str(user_id), model._model_name, cache_key),
            value=model.model_dump(mode="json"),
            timeout=getattr(model, "_cache_timeout", _get_config_value("CACHE_DEFAULT_TIMEOUT", Config.CACHE_DEFAULT_TIMEOUT)),
        )
        return model
    except Exception:
        logger.exception("Failed to add model to cache")
        return None


def get_model_from_cache(model_name: str, cache_key: str, user_id: int | str) -> dict[str, Any] | None:
    return cache.get(cache.model_detail_key(str(user_id), model_name, cache_key))


def init(app):
    cache.init(app)

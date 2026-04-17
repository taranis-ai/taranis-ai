from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from models.assess import NewsItem
from models.user import UserProfile

from frontend.cache import (
    FrontendCache,
    add_user_to_cache,
    cache,
    get_cached_users,
    get_user_from_cache,
    list_cache_keys,
)


class _InMemoryBackend:
    def __init__(self):
        self.store: dict[str, Any] = {}

    @property
    def enabled(self) -> bool:
        return True

    def get(self, key: str) -> Any:
        return self.store.get(key)

    def set(self, key: str, value: Any, timeout: int | None = None) -> bool:
        self.store[key] = value
        return True

    def delete(self, key: str) -> int:
        return int(self.store.pop(key, None) is not None)

    def clear(self) -> int:
        deleted = len(self.store)
        self.store.clear()
        return deleted

    def scan_keys(self, pattern: str) -> list[str]:
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return sorted(key for key in self.store if key.startswith(prefix))
        return sorted(key for key in self.store if key == pattern)


@contextmanager
def _swap_backend(new_backend: _InMemoryBackend) -> Iterator[None]:
    original_backend = cache._backend
    original_prefix = cache.key_prefix
    original_timeout = cache.default_timeout
    cache._backend = new_backend
    cache.key_prefix = "test_frontend"
    cache.default_timeout = 300
    try:
        yield
    finally:
        cache._backend = original_backend
        cache.key_prefix = original_prefix
        cache.default_timeout = original_timeout


def test_cache_is_disabled_by_default_for_unit_tests(app):
    with app.app_context():
        assert cache.enabled is False
        assert cache.get("missing") is None
        assert cache.set("key", {"value": 1}) is False
        assert list_cache_keys() == []
        assert get_cached_users() == []


def test_user_profile_cache_key_is_user_scoped_and_model_derived():
    local_cache = FrontendCache()
    local_cache.key_prefix = "taranis_frontend"

    assert local_cache.user_profile_key("alice") == "taranis_frontend:user:alice:model:user_profile:profile:self"


def test_news_item_detail_cache_key_uses_news_item_model_name():
    local_cache = FrontendCache()
    local_cache.key_prefix = "taranis_frontend"

    assert (
        local_cache.model_detail_key("alice", NewsItem._model_name, "news-1") == "taranis_frontend:user:alice:model:news_item:detail:news-1"
    )


def test_user_cache_round_trips_user_profile(app):
    backend = _InMemoryBackend()
    user_payload = {
        "id": 1,
        "username": "admin",
        "name": "Arthur Dent",
        "organization": {"id": 1, "name": "Galactic Government"},
        "permissions": ["ALL"],
        "profile": {},
        "roles": [{"id": 1, "name": "Admin"}],
    }

    with app.app_context(), _swap_backend(backend):
        cached_user = add_user_to_cache(user_payload)

        assert isinstance(cached_user, UserProfile)
        assert get_user_from_cache("admin") == cached_user
        assert list_cache_keys() == ["test_frontend:user:admin:model:user_profile:profile:self"]
        assert get_cached_users() == [cached_user]

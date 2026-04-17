from unittest.mock import Mock

import frontend.cache as cache_module
from frontend.cache import cache, invalidate_cache_keys


def test_invalidate_cache_keys_matches_normalized_suffix(app):
    with app.app_context():
        cache.set("user1__config_schedule", "scheduled")
        cache.set("user1__config_workers_active", "active")

        invalidated = invalidate_cache_keys("config/schedule")

        assert invalidated == 1
        assert cache.get("user1__config_schedule") is None
        assert cache.get("user1__config_workers_active") == "active"

        cache.delete("user1__config_workers_active")


def test_invalidate_cache_keys_ignores_empty_suffix(app):
    with app.app_context():
        cache.set("user1__config_schedule", "scheduled")

        invalidated = invalidate_cache_keys("")

        assert invalidated == 0
        assert cache.get("user1__config_schedule") == "scheduled"

        cache.delete("user1__config_schedule")


def test_invalidate_cache_keys_falls_back_to_clear(app, monkeypatch):
    clear = Mock()

    with app.app_context():
        monkeypatch.setattr(cache_module, "_get_cache_store", lambda: None)
        monkeypatch.setattr(cache_module.cache, "clear", clear)

        invalidated = invalidate_cache_keys("config/schedule")

    assert invalidated == -1
    clear.assert_called_once()

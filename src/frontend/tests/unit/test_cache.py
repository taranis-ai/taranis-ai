from models.assess import NewsItem
from models.user import UserProfile

from frontend.cache import FrontendCache, add_user_to_cache, cache, get_cache_keys, get_cached_users, get_user_from_cache


def test_cache_is_disabled_by_default_for_unit_tests(app):
    with app.app_context():
        assert cache.enabled is False
        assert cache.get("missing") is None
        assert cache.set("key", {"value": 1}) is False
        assert get_cache_keys() == []
        assert get_cached_users() == []


def test_user_profile_cache_key_is_user_scoped_and_model_derived():
    local_cache = FrontendCache()

    assert local_cache.user_profile_key("alice") == "taranis_frontend:user:alice:model:user_profile:profile:self"


def test_news_item_detail_cache_key_uses_news_item_model_name():
    local_cache = FrontendCache()

    assert (
        local_cache.model_detail_key("alice", NewsItem._model_name, "news-1") == "taranis_frontend:user:alice:model:news_item:detail:news-1"
    )


def test_user_cache_round_trips_user_profile(app, test_cache_backend):
    user_payload = {
        "id": 1,
        "username": "admin",
        "name": "Arthur Dent",
        "organization": {"id": 1, "name": "Galactic Government"},
        "permissions": ["ALL"],
        "profile": {},
        "roles": [{"id": 1, "name": "Admin"}],
    }

    with app.app_context():
        cached_user = add_user_to_cache(user_payload)

        assert isinstance(cached_user, UserProfile)
        assert get_user_from_cache("admin") == cached_user
        assert get_cache_keys() == ["taranis_frontend:user:admin:model:user_profile:profile:self"]
        assert get_cached_users() == [cached_user]

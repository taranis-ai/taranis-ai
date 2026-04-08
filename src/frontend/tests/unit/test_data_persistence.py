from unittest.mock import Mock

import frontend.data_persistence as data_persistence_module
from frontend.cache import cache
from frontend.data_persistence import DataPersistenceLayer
from models.admin import Job, OSINTSource
from models.types import COLLECTOR_TYPES


def test_get_objects_by_endpoint_caches_empty_results(app, monkeypatch):
    cache_key = "user1__config_empty"
    api = Mock()
    api.api_get.return_value = {"items": [], "total_count": 0}

    with app.app_context():
        monkeypatch.setattr(data_persistence_module, "get_jwt_identity", lambda: "user1")
        cache.delete(cache_key)

        persistence = DataPersistenceLayer(jwt_token="token")
        persistence.api = api

        first_result = persistence.get_objects_by_endpoint(Job, "/config/empty")
        second_result = persistence.get_objects_by_endpoint(Job, "/config/empty")

        assert first_result.total_count == 0
        assert second_result.total_count == 0
        assert list(second_result) == []
        assert cache.get(cache_key) is not None
        assert api.api_get.call_count == 1

        cache.delete(cache_key)


def test_update_object_invalidates_scheduler_caches_for_osint_sources(app, monkeypatch):
    response = Mock()
    response.ok = True
    response.json.return_value = {"id": "source-1"}

    api = Mock()
    api.api_put.return_value = response

    with app.test_request_context():
        monkeypatch.setattr(data_persistence_module, "get_jwt_identity", lambda: "user1")
        cache.set("user1__config_osint-sources", "sources")
        cache.set("user1__config_schedule", "schedule")
        cache.set("user1__config_workers_dashboard", "dashboard")

        persistence = DataPersistenceLayer(jwt_token="token")
        persistence.api = api
        source = OSINTSource(
            id="source-1",
            name="Source",
            type=COLLECTOR_TYPES.RSS_COLLECTOR,
            parameters={"FEED_URL": "https://example.com/feed.xml"},
        )

        persistence.update_object(source, "source-1")

        assert cache.get("user1__config_osint-sources") is None
        assert cache.get("user1__config_schedule") is None
        assert cache.get("user1__config_workers_dashboard") is None

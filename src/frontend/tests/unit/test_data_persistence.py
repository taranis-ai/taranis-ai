from unittest.mock import Mock

import frontend.data_persistence as data_persistence_module
from frontend.cache import cache
from frontend.data_persistence import DataPersistenceLayer
from models.admin import Job


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

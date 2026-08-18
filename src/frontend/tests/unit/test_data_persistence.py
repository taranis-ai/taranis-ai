from unittest.mock import Mock

from models.admin import ActiveJob, OSINTSource
from models.types import COLLECTOR_TYPES

import frontend.data_persistence as data_persistence_module
from frontend.cache import cache, get_cache_keys
from frontend.cache_models import PagingData
from frontend.data_persistence import DataPersistenceLayer


def test_get_objects_by_endpoint_caches_empty_results(app, monkeypatch, test_cache_backend):
    api = Mock()
    api.api_get.return_value = {"items": [], "total_count": 0}

    with app.app_context():
        monkeypatch.setattr(data_persistence_module, "get_jwt_identity", lambda: "user1")

        persistence = DataPersistenceLayer(jwt_token="token")
        persistence.api = api
        cache_key = persistence.make_list_cache_key(ActiveJob, "/config/empty")

        first_result = persistence.get_objects_by_endpoint(ActiveJob, "/config/empty")
        second_result = persistence.get_objects_by_endpoint(ActiveJob, "/config/empty")

        assert first_result.total_count == 0
        assert second_result.total_count == 0
        assert list(second_result) == []
        assert get_cache_keys() == [cache_key]
        assert api.api_get.call_count == 1


def test_update_object_does_not_invalidate_local_cache(app, monkeypatch, test_cache_backend):
    response = Mock()
    response.ok = True
    api = Mock()
    api.api_patch.return_value = response

    with app.test_request_context():
        monkeypatch.setattr(data_persistence_module, "get_jwt_identity", lambda: "user1")
        story_cache_key = cache.model_list_key("user1", "osint_source", "list-suffix")
        worker_cache_key = cache.model_list_key("user1", "worker_stats", "worker-suffix")
        cache.set(story_cache_key, {"items": []})
        cache.set(worker_cache_key, {"items": []})

        persistence = DataPersistenceLayer(jwt_token="token")
        persistence.api = api
        source = OSINTSource(
            id="source-1",
            name="Source",
            type=COLLECTOR_TYPES.RSS_COLLECTOR,
            parameters={"FEED_URL": "https://example.com/feed.xml"},
        )

        persistence.update_object(source, "source-1")

        api.api_patch.assert_called_once()
        api.api_put.assert_not_called()

        assert cache.get(story_cache_key) == {"items": []}
        assert cache.get(worker_cache_key) == {"items": []}


def test_get_objects_caches_active_jobs(app, monkeypatch, test_cache_backend):
    api = Mock()
    api.api_get.return_value = {"items": [], "total_count": 0}

    with app.app_context():
        monkeypatch.setattr(data_persistence_module, "get_jwt_identity", lambda: "user1")

        persistence = DataPersistenceLayer(jwt_token="token")
        persistence.api = api
        paging_data = PagingData().set_fetch_all()
        cache_key = persistence.make_list_cache_key(ActiveJob, persistence.get_endpoint(ActiveJob), paging_data)

        persistence.get_objects(ActiveJob)
        persistence.get_objects(ActiveJob)

        assert get_cache_keys() == [cache_key]
        assert api.api_get.call_count == 1


def test_invalidate_cache_forwards_suffix_without_scope_mapping(app):
    response = Mock()
    api = Mock()
    api.api_post.return_value = response

    with app.test_request_context():
        persistence = DataPersistenceLayer(jwt_token="token")
        persistence.api = api

        result = persistence.invalidate_cache("config/workers/stats")

    assert result is response
    api.api_post.assert_called_once_with(
        "/admin/cache/invalidate",
        json_data={"mode": "model", "model": "config/workers/stats"},
    )

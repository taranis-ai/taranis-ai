import fakeredis

from core.service.cache_invalidation import FrontendCacheInvalidationService


def _build_service(keys: list[str]) -> FrontendCacheInvalidationService:
    client = fakeredis.FakeRedis(decode_responses=True)
    for key in keys:
        client.set(key, "1")

    service = FrontendCacheInvalidationService()
    service._client = client
    return service


def test_invalidate_model_clears_keys_across_all_user_namespaces(monkeypatch):
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_ENABLED", True)
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_KEY_PREFIX", "taranis_frontend")
    service = _build_service(
        [
            "taranis_frontend:user:alice:model:story:list:one",
            "taranis_frontend:user:alice:model:story:detail:1",
            "taranis_frontend:user:bob:model:story:detail:2",
            "taranis_frontend:user:bob:model:product:detail:7",
        ]
    )

    deleted = service.invalidate_model("story")

    assert deleted == 3
    assert set(service._client.scan_iter(match="*")) == {"taranis_frontend:user:bob:model:product:detail:7"}


def test_invalidate_model_for_object_clears_detail_and_lists_only(monkeypatch):
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_ENABLED", True)
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_KEY_PREFIX", "taranis_frontend")
    service = _build_service(
        [
            "taranis_frontend:user:alice:model:story:list:one",
            "taranis_frontend:user:alice:model:story:detail:1",
            "taranis_frontend:user:alice:model:story:detail:2",
            "taranis_frontend:user:bob:model:story:list:two",
        ]
    )

    deleted = service.invalidate_model("story", object_id="1")

    assert deleted == 3
    assert set(service._client.scan_iter(match="*")) == {"taranis_frontend:user:alice:model:story:detail:2"}


def test_invalidate_scope_schedule_clears_scheduler_related_models(monkeypatch):
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_ENABLED", True)
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_KEY_PREFIX", "taranis_frontend")
    service = _build_service(
        [
            "taranis_frontend:user:alice:model:job:list:one",
            "taranis_frontend:user:alice:model:scheduler_dashboard:detail:singleton",
            "taranis_frontend:user:alice:model:task_history_response:detail:singleton",
            "taranis_frontend:user:alice:model:story:list:one",
        ]
    )

    deleted = service.invalidate_scope("schedule")

    assert deleted == 3
    assert set(service._client.scan_iter(match="*")) == {"taranis_frontend:user:alice:model:story:list:one"}

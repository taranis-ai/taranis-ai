from fnmatch import fnmatch

from core.service.cache_invalidation import FrontendCacheInvalidationService


class _FakeRedis:
    def __init__(self, keys: list[str]):
        self.keys = set(keys)

    def ping(self):
        return True

    def scan_iter(self, match: str, count: int = 1000):
        yield from sorted(key for key in self.keys if fnmatch(key, match))

    def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self.keys:
                self.keys.remove(key)
                deleted += 1
        return deleted


def test_invalidate_model_clears_keys_across_all_user_namespaces(monkeypatch):
    service = FrontendCacheInvalidationService()
    service._client = _FakeRedis(
        [
            "taranis_frontend:user:alice:model:story:list:one",
            "taranis_frontend:user:alice:model:story:detail:1",
            "taranis_frontend:user:bob:model:story:detail:2",
            "taranis_frontend:user:bob:model:product:detail:7",
        ]
    )
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_ENABLED", True)
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_KEY_PREFIX", "taranis_frontend")

    deleted = service.invalidate_model("story")

    assert deleted == 3
    assert service._client.keys == {"taranis_frontend:user:bob:model:product:detail:7"}


def test_invalidate_model_for_object_clears_detail_and_lists_only(monkeypatch):
    service = FrontendCacheInvalidationService()
    service._client = _FakeRedis(
        [
            "taranis_frontend:user:alice:model:story:list:one",
            "taranis_frontend:user:alice:model:story:detail:1",
            "taranis_frontend:user:alice:model:story:detail:2",
            "taranis_frontend:user:bob:model:story:list:two",
        ]
    )
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_ENABLED", True)
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_KEY_PREFIX", "taranis_frontend")

    deleted = service.invalidate_model("story", object_id="1")

    assert deleted == 3
    assert service._client.keys == {"taranis_frontend:user:alice:model:story:detail:2"}


def test_invalidate_scope_schedule_clears_scheduler_related_models(monkeypatch):
    service = FrontendCacheInvalidationService()
    service._client = _FakeRedis(
        [
            "taranis_frontend:user:alice:model:job:list:one",
            "taranis_frontend:user:alice:model:scheduler_dashboard:detail:singleton",
            "taranis_frontend:user:alice:model:task_history_response:detail:singleton",
            "taranis_frontend:user:alice:model:story:list:one",
        ]
    )
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_ENABLED", True)
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_KEY_PREFIX", "taranis_frontend")

    deleted = service.invalidate_scope("schedule")

    assert deleted == 3
    assert service._client.keys == {"taranis_frontend:user:alice:model:story:list:one"}

import fakeredis
import pytest

from core.service.cache_invalidation import (
    SCOPE_ASSESS_VIEWS,
    SCOPE_SCHEDULE,
    SCOPE_SCHEDULE_STATUS,
    SCOPE_USER_VIEWS,
    FrontendCacheInvalidationService,
)


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
            "taranis_frontend:user:alice:model:task_history_response:detail:singleton",
            "taranis_frontend:user:alice:model:story:list:one",
        ]
    )

    deleted = service.invalidate_scope(SCOPE_SCHEDULE)

    assert deleted == 2
    assert set(service._client.scan_iter(match="*")) == {"taranis_frontend:user:alice:model:story:list:one"}


def test_invalidate_scope_schedule_status_keeps_queue_runtime_models(monkeypatch):
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_ENABLED", True)
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_KEY_PREFIX", "taranis_frontend")
    service = _build_service(
        [
            "taranis_frontend:user:alice:model:job:list:one",
            "taranis_frontend:user:alice:model:task_history_response:detail:singleton",
            "taranis_frontend:user:alice:model:active_job:list:one",
            "taranis_frontend:user:alice:model:failed_job:list:one",
            "taranis_frontend:user:alice:model:queue_status:list:one",
            "taranis_frontend:user:alice:model:worker_stats:detail:singleton",
        ]
    )

    deleted = service.invalidate_scope(SCOPE_SCHEDULE_STATUS)

    assert deleted == 2
    assert set(service._client.scan_iter(match="*")) == {
        "taranis_frontend:user:alice:model:active_job:list:one",
        "taranis_frontend:user:alice:model:failed_job:list:one",
        "taranis_frontend:user:alice:model:queue_status:list:one",
        "taranis_frontend:user:alice:model:worker_stats:detail:singleton",
    }


def test_invalidate_scope_uses_object_ids_for_scoped_models(monkeypatch):
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_ENABLED", True)
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_KEY_PREFIX", "taranis_frontend")
    service = _build_service(
        [
            "taranis_frontend:user:alice:model:story:list:one",
            "taranis_frontend:user:alice:model:news_item:list:one",
            "taranis_frontend:user:alice:model:news_item:detail:1",
            "taranis_frontend:user:alice:model:news_item:detail:2",
            "taranis_frontend:user:alice:model:filter_lists:detail:singleton",
        ]
    )

    deleted = service.invalidate_scope(SCOPE_ASSESS_VIEWS, object_ids={"news_item": "1"})

    assert deleted == 4
    assert set(service._client.scan_iter(match="*")) == {"taranis_frontend:user:alice:model:news_item:detail:2"}


def test_invalidate_scope_user_views_clears_user_facing_content_models(monkeypatch):
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_ENABLED", True)
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_KEY_PREFIX", "taranis_frontend")
    service = _build_service(
        [
            "taranis_frontend:user:alice:model:dashboard:detail:singleton",
            "taranis_frontend:user:alice:model:trending_clusters:list:one",
            "taranis_frontend:user:alice:model:clusters:list:one",
            "taranis_frontend:user:alice:model:story_conflicts:list:one",
            "taranis_frontend:user:alice:model:news_item_conflict:list:one",
            "taranis_frontend:user:alice:model:story:list:one",
            "taranis_frontend:user:alice:model:news_item:list:one",
            "taranis_frontend:user:alice:model:report_item:list:one",
            "taranis_frontend:user:alice:model:filter_lists:detail:singleton",
            "taranis_frontend:user:alice:model:report:list:one",
            "taranis_frontend:user:alice:model:product:list:one",
            "taranis_frontend:user:alice:model:asset:list:one",
        ]
    )

    deleted = service.invalidate_scope(SCOPE_USER_VIEWS)

    assert deleted == 11
    assert set(service._client.scan_iter(match="*")) == {"taranis_frontend:user:alice:model:asset:list:one"}


@pytest.mark.parametrize("scope", ["report_views", "story_views", "story_report_views", "user_views"])
def test_report_editor_cache_is_cleared_when_its_content_changes(monkeypatch, scope):
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_ENABLED", True)
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_KEY_PREFIX", "taranis_frontend")
    service = _build_service(
        [
            "taranis_frontend:user:alice:model:report_editor:detail:one",
            "taranis_frontend:user:bob:model:report_editor:detail:one",
            "taranis_frontend:user:alice:model:product:list:choices",
        ]
    )

    service.invalidate_scope(scope, object_ids={"report": "one"})

    assert not list(service._client.scan_iter(match="*:model:report_editor:*"))


@pytest.mark.parametrize("scope", ["publish_views", "report_views", "user_views"])
def test_product_metadata_cache_is_cleared_with_product_choices(monkeypatch, scope):
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_ENABLED", True)
    monkeypatch.setattr("core.service.cache_invalidation.Config.CACHE_KEY_PREFIX", "taranis_frontend")
    service = _build_service(
        [
            "taranis_frontend:user:alice:model:product_metadata:detail:one",
            "taranis_frontend:user:bob:model:product_metadata:detail:one",
            "taranis_frontend:user:alice:model:product:list:choices",
        ]
    )

    assert service.invalidate_scope(scope) == 3
    assert not list(service._client.scan_iter())

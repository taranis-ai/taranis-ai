from collections.abc import Iterable, Mapping
from typing import cast

from models.cache_contract import (
    build_model_detail_pattern,
    build_model_list_pattern,
    build_model_pattern,
    build_namespace_pattern,
    build_user_profile_pattern,
    get_secret_value,
)
from redis import Redis

from core.config import Config
from core.log import logger


SCOPE_SCHEDULE = "schedule"
SCOPE_SCHEDULE_STATUS = "schedule_status"
SCOPE_TRENDING_CLUSTERS = "trending_clusters"
SCOPE_ASSESS_VIEWS = "assess_views"
SCOPE_STORY_VIEWS = "story_views"
SCOPE_STORY_REPORT_VIEWS = "story_report_views"
SCOPE_REPORT_VIEWS = "report_views"
SCOPE_PUBLISH_VIEWS = "publish_views"
SCOPE_USER_VIEWS = "user_views"


SCOPE_MODEL_NAMES: dict[str, tuple[str, ...]] = {
    SCOPE_SCHEDULE: (
        "job",
        "active_job",
        "failed_job",
        "queue_status",
        "worker_stats",
        "scheduler_dashboard",
        "task_history_response",
    ),
    SCOPE_SCHEDULE_STATUS: (
        "job",
        "scheduler_dashboard",
        "task_history_response",
    ),
    SCOPE_TRENDING_CLUSTERS: ("trending_clusters",),
    SCOPE_ASSESS_VIEWS: ("story", "news_item", "filter_lists"),
    SCOPE_STORY_VIEWS: ("story", "news_item", "report_item"),
    SCOPE_STORY_REPORT_VIEWS: ("story", "report_item"),
    SCOPE_REPORT_VIEWS: ("report", "story", "product"),
    SCOPE_PUBLISH_VIEWS: ("product",),
    SCOPE_USER_VIEWS: (
        "dashboard",
        "trending_clusters",
        "clusters",
        "story_conflicts",
        "news_item_conflict",
        "story",
        "news_item",
        "report_item",
        "filter_lists",
        "report",
        "product",
    ),
}


class FrontendCacheInvalidationService:
    def __init__(self):
        self._client: Redis | None = None
        self._disabled = False

    @property
    def scope_names(self) -> set[str]:
        return set(SCOPE_MODEL_NAMES)

    def _get_client(self) -> Redis | None:
        if self._disabled or not Config.CACHE_ENABLED:
            return None
        if self._client is not None:
            return self._client

        redis_url = Config.CACHE_REDIS_URL or Config.REDIS_URL
        if not redis_url:
            return None

        try:
            redis_password = get_secret_value(Config.CACHE_REDIS_PASSWORD) or get_secret_value(Config.REDIS_PASSWORD)
            self._client = Redis.from_url(redis_url, password=redis_password, decode_responses=True)
            self._client.ping()
        except Exception:
            logger.exception("Failed to initialize frontend cache invalidation Redis client")
            self._disabled = True
            self._client = None
        return self._client

    def _delete_matching_patterns(self, patterns: Iterable[str]) -> int:
        client = self._get_client()
        if client is None:
            return 0

        keys_to_delete: list[str] = []
        seen: set[str] = set()
        for pattern in patterns:
            for key in client.scan_iter(match=pattern, count=1000):
                key_str = str(key)
                if key_str in seen:
                    continue
                seen.add(key_str)
                keys_to_delete.append(key_str)

        return cast(int, client.delete(*keys_to_delete)) if keys_to_delete else 0

    def invalidate_all(self) -> int:
        return self._delete_matching_patterns([build_namespace_pattern(Config.CACHE_KEY_PREFIX)])

    def invalidate_model(self, model_name: str, object_id: str | int | None = None) -> int:
        if object_id is None:
            patterns = [build_model_pattern(Config.CACHE_KEY_PREFIX, model_name)]
        else:
            patterns = [
                build_model_detail_pattern(Config.CACHE_KEY_PREFIX, model_name, object_id),
                build_model_list_pattern(Config.CACHE_KEY_PREFIX, model_name),
            ]
        return self._delete_matching_patterns(patterns)

    def get_scope_model_names(self, scope_name: str) -> tuple[str, ...]:
        model_names = SCOPE_MODEL_NAMES.get(scope_name)
        if model_names is None:
            logger.warning(f"Unknown frontend cache invalidation scope: {scope_name}")
            return ()
        return model_names

    def invalidate_scope(self, scope_name: str, object_ids: Mapping[str, str | int] | None = None) -> int:
        object_ids = object_ids or {}
        return sum(self.invalidate_model(model_name, object_ids.get(model_name)) for model_name in self.get_scope_model_names(scope_name))

    def invalidate_user_profile(self, username: str) -> int:
        return self._delete_matching_patterns([build_user_profile_pattern(Config.CACHE_KEY_PREFIX, username)])


cache_invalidation_service = FrontendCacheInvalidationService()


def invalidate_frontend_cache_on_success(
    status_code: int,
    *,
    full: bool = False,
    models: Iterable[str] = (),
    scopes: Iterable[str] = (),
    user_profiles: Iterable[str] = (),
    object_ids: dict[str, str | int] | None = None,
) -> int:
    if not 200 <= status_code < 300:
        return 0

    deleted = 0
    object_ids = object_ids or {}
    if full:
        deleted += cache_invalidation_service.invalidate_all()

    for username in user_profiles:
        deleted += cache_invalidation_service.invalidate_user_profile(username)

    model_names: list[str] = []
    for scope_name in scopes:
        model_names.extend(cache_invalidation_service.get_scope_model_names(scope_name))
    model_names.extend(models)

    for model_name in dict.fromkeys(model_names):
        deleted += cache_invalidation_service.invalidate_model(model_name, object_ids.get(model_name))

    return deleted

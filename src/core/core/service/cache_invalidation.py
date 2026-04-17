from collections.abc import Iterable
from typing import Any

from redis import Redis

from core.config import Config
from core.log import logger


SCOPE_MODEL_NAMES: dict[str, tuple[str, ...]] = {
    "schedule": (
        "job",
        "active_job",
        "failed_job",
        "queue_status",
        "worker_stats",
        "scheduler_dashboard",
        "task_history_response",
    ),
    "trending_clusters": ("trending_clusters",),
}


def _get_secret_value(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "get_secret_value"):
        return value.get_secret_value()
    return str(value) or None


def _is_success_status(status_code: int) -> bool:
    return 200 <= status_code < 300


class FrontendCacheInvalidationService:
    def __init__(self):
        self._client: Redis | None = None
        self._disabled = False

    @property
    def scope_names(self) -> set[str]:
        return set(SCOPE_MODEL_NAMES)

    def _get_redis_url(self) -> str | None:
        return Config.CACHE_REDIS_URL or Config.REDIS_URL

    def _get_redis_password(self) -> str | None:
        return _get_secret_value(Config.CACHE_REDIS_PASSWORD) or _get_secret_value(Config.REDIS_PASSWORD)

    def _get_client(self) -> Redis | None:
        if self._disabled or not Config.CACHE_ENABLED:
            return None
        if self._client is not None:
            return self._client

        redis_url = self._get_redis_url()
        if not redis_url:
            return None

        try:
            self._client = Redis.from_url(redis_url, password=self._get_redis_password(), decode_responses=True)
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

        deleted = 0
        batch: list[str] = []
        seen: set[str] = set()
        for pattern in patterns:
            for key in client.scan_iter(match=pattern, count=1000):
                key_str = str(key)
                if key_str in seen:
                    continue
                seen.add(key_str)
                batch.append(key_str)
                if len(batch) >= 500:
                    deleted += int(client.delete(*batch))
                    batch.clear()

        if batch:
            deleted += int(client.delete(*batch))
        return deleted

    def invalidate_all(self) -> int:
        return self._delete_matching_patterns([f"{Config.CACHE_KEY_PREFIX}:*"])

    def invalidate_model(self, model_name: str, object_id: str | int | None = None) -> int:
        if object_id is None:
            patterns = [f"{Config.CACHE_KEY_PREFIX}:user:*:model:{model_name}:*"]
        else:
            patterns = [
                f"{Config.CACHE_KEY_PREFIX}:user:*:model:{model_name}:detail:{object_id}",
                f"{Config.CACHE_KEY_PREFIX}:user:*:model:{model_name}:list:*",
            ]
        return self._delete_matching_patterns(patterns)

    def invalidate_scope(self, scope_name: str) -> int:
        model_names = SCOPE_MODEL_NAMES.get(scope_name)
        if model_names is None:
            logger.warning("Unknown frontend cache invalidation scope: %s", scope_name)
            return 0
        return sum(self.invalidate_model(model_name) for model_name in model_names)

    def invalidate_user_profile(self, username: str) -> int:
        pattern = f"{Config.CACHE_KEY_PREFIX}:user:{username}:model:user_profile:*"
        return self._delete_matching_patterns([pattern])


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
    if not _is_success_status(status_code):
        return 0

    deleted = 0
    if full:
        deleted += cache_invalidation_service.invalidate_all()

    for username in user_profiles:
        deleted += cache_invalidation_service.invalidate_user_profile(username)

    for scope_name in scopes:
        deleted += cache_invalidation_service.invalidate_scope(scope_name)

    object_ids = object_ids or {}
    for model_name in models:
        deleted += cache_invalidation_service.invalidate_model(model_name, object_ids.get(model_name))

    return deleted

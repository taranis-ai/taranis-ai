from typing import Any

from models.user import UserProfile


CACHE_ENABLED_DEFAULT = True
CACHE_DEFAULT_TIMEOUT_DEFAULT = 300
CACHE_KEY_PREFIX_DEFAULT = "taranis_frontend"

CACHE_USER_SEGMENT = "user"
CACHE_MODEL_SEGMENT = "model"
CACHE_LIST_KIND = "list"
CACHE_DETAIL_KIND = "detail"
CACHE_PROFILE_KIND = "profile"
CACHE_SINGLETON_SUFFIX = "singleton"
CACHE_DEFAULT_LIST_SUFFIX = "default"
CACHE_USER_PROFILE_MODEL_NAME = UserProfile._model_name


def get_secret_value(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "get_secret_value"):
        return value.get_secret_value()
    text = str(value)
    return text or None


def normalize_cache_suffix(value: str | int | None) -> str:
    if value in (None, ""):
        return CACHE_DEFAULT_LIST_SUFFIX
    return str(value)


def build_cache_key(prefix: str, username: str, model_name: str, kind: str, suffix: str | int | None) -> str:
    return f"{prefix}:{CACHE_USER_SEGMENT}:{username}:{CACHE_MODEL_SEGMENT}:{model_name}:{kind}:{normalize_cache_suffix(suffix)}"


def build_model_list_key(prefix: str, username: str, model_name: str, suffix: str | int | None) -> str:
    return build_cache_key(prefix, username, model_name, CACHE_LIST_KIND, suffix)


def build_model_detail_key(prefix: str, username: str, model_name: str, object_id: str | int | None = None) -> str:
    return build_cache_key(prefix, username, model_name, CACHE_DETAIL_KIND, object_id or CACHE_SINGLETON_SUFFIX)


def build_user_profile_key(prefix: str, username: str) -> str:
    return build_cache_key(prefix, username, CACHE_USER_PROFILE_MODEL_NAME, CACHE_PROFILE_KIND, "self")


def build_namespace_pattern(prefix: str) -> str:
    return f"{prefix}:*"


def build_model_pattern(prefix: str, model_name: str) -> str:
    return f"{prefix}:{CACHE_USER_SEGMENT}:*:{CACHE_MODEL_SEGMENT}:{model_name}:*"


def build_model_list_pattern(prefix: str, model_name: str) -> str:
    return f"{prefix}:{CACHE_USER_SEGMENT}:*:{CACHE_MODEL_SEGMENT}:{model_name}:{CACHE_LIST_KIND}:*"


def build_model_detail_pattern(prefix: str, model_name: str, object_id: str | int) -> str:
    return f"{prefix}:{CACHE_USER_SEGMENT}:*:{CACHE_MODEL_SEGMENT}:{model_name}:{CACHE_DETAIL_KIND}:{object_id}"


def build_user_profile_pattern(prefix: str, username: str = "*") -> str:
    return f"{prefix}:{CACHE_USER_SEGMENT}:{username}:{CACHE_MODEL_SEGMENT}:{CACHE_USER_PROFILE_MODEL_NAME}:{CACHE_PROFILE_KIND}:*"


def parse_user_profile_key(key: str) -> str | None:
    parts = key.split(":")
    if len(parts) != 7:
        return None

    prefix, user_segment, username, model_segment, model_name, kind, suffix = parts
    if (
        not prefix
        or user_segment != CACHE_USER_SEGMENT
        or model_segment != CACHE_MODEL_SEGMENT
        or model_name != CACHE_USER_PROFILE_MODEL_NAME
        or kind != CACHE_PROFILE_KIND
        or suffix != "self"
    ):
        return None

    return username

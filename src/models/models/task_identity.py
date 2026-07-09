from typing import Any


def get_task_name_from_job(job: Any, meta: dict[str, Any] | None = None) -> str | None:
    normalized_meta = meta if isinstance(meta, dict) else {}
    task_name = get_meta_string(normalized_meta, "task")
    if task_name:
        return task_name

    return _normalize_short_name(getattr(job, "func_name", "") or "")


def get_task_name_from_spec(spec: dict[str, Any]) -> str | None:
    meta = spec.get("meta")
    task_name = get_meta_string(meta if isinstance(meta, dict) else None, "task")
    if task_name:
        return task_name

    return _normalize_short_name(spec.get("func_path") or "")


def get_meta_string(meta: dict[str, Any] | None, key: str) -> str | None:
    if not isinstance(meta, dict):
        return None

    value = meta.get(key)
    if value is None:
        return None

    normalized = str(value).strip()
    return normalized or None


def _normalize_short_name(func_name: str) -> str | None:
    short_name = func_name.rsplit(".", 1)[-1].strip()
    if not short_name:
        return None
    return "collector_task" if short_name == "fetch_single_news_item" else short_name

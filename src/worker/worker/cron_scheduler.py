import inspect
import json
import os
import time
from collections.abc import Awaitable
from datetime import datetime, timezone
from typing import Any, TypeVar, cast

from croniter import croniter
from models.task import CronTaskSpec
from models.task_submission_meta import build_task_submission_meta, is_worker_task_payload
from pydantic import ValidationError
from redis import Redis
from rq import Queue

from worker.config import Config
from worker.log import logger


DEFS_KEY = "rq:cron:def"  # HASH: job_id -> JSON spec (written by core QueueManager)
NEXT_KEY = "rq:cron:next"  # ZSET: job_id -> next_run_unix_ts
LOCK_KEY = "rq:cron:leader"  # STRING: leader node id
ENQUEUE_KEY_PREFIX = "rq:cron:enqueue:"
ENQUEUE_KEY_TTL_SECONDS = 300

TASK_FUNCTION_MAP = {
    "collector_task": "worker.collectors.collector_tasks.collector_task",
    "bot_task": "worker.bots.bot_tasks.bot_task",
    "cleanup_token_blacklist": "worker.misc.misc_tasks.cleanup_token_blacklist",
}

T = TypeVar("T")


def _sync_response(value: T | Awaitable[T], operation: str) -> T:
    if inspect.isawaitable(value):
        raise TypeError(f"{operation} returned an awaitable; cron scheduler requires a synchronous Redis client")
    return cast(T, value)


def _decode(value: bytes | str | Awaitable[bytes | str], operation: str = "Redis response") -> str:
    decoded_value = _sync_response(value, operation)
    if isinstance(decoded_value, bytes):
        return decoded_value.decode()
    if isinstance(decoded_value, (bytearray, memoryview)):
        return bytes(decoded_value).decode()
    return decoded_value


def _normalize_spec(spec: dict[str, Any]) -> dict[str, Any] | None:
    try:
        return CronTaskSpec.model_validate(spec).model_dump()
    except ValidationError as exc:
        logger.warning(f"Ignoring invalid cron scheduler spec: {exc}")
        return None


def _load_spec(redis: Redis, job_id: str) -> dict[str, Any] | None:
    raw_spec = cast(bytes | str | None, _sync_response(redis.hget(DEFS_KEY, job_id), "redis.hget"))
    if not raw_spec:
        return None
    parsed = json.loads(_decode(raw_spec, "redis.hget"))
    return _normalize_spec(parsed)


def _sync_next_index(redis: Redis, base_ts: float) -> dict[str, dict[str, Any]]:
    raw_specs = cast(dict[bytes | str, bytes | str], _sync_response(redis.hgetall(DEFS_KEY), "redis.hgetall"))
    specs: dict[str, dict[str, Any]] = {}

    for raw_job_id, raw_spec in raw_specs.items():
        job_id = _decode(raw_job_id, "redis.hgetall key")
        if parsed := _normalize_spec(json.loads(_decode(raw_spec, "redis.hgetall value"))):
            specs[job_id] = parsed

    next_ids = {
        _decode(raw_id, "redis.zrange item")
        for raw_id in cast(list[bytes | str], _sync_response(redis.zrange(NEXT_KEY, 0, -1), "redis.zrange"))
    }
    spec_ids = set(specs.keys())

    if stale_ids := next_ids - spec_ids:
        redis.zrem(NEXT_KEY, *stale_ids)

    missing_ids = spec_ids - next_ids
    for job_id in missing_ids:
        try:
            next_ts = compute_next(specs[job_id], base_ts)
        except ValueError as exc:
            logger.warning(f"Skipping next-run registration for invalid cron scheduler spec {job_id}: {exc}")
            continue
        redis.zadd(NEXT_KEY, {job_id: next_ts})

    return specs


def compute_next(spec: dict[str, Any], base_ts: float) -> float:
    if spec.get("cron"):
        dt = datetime.fromtimestamp(base_ts, tz=timezone.utc)
        return croniter(spec["cron"], dt).get_next(datetime).timestamp()
    interval = spec.get("interval")
    if interval is not None:
        return base_ts + int(interval)
    raise ValueError("CronTaskSpec must provide exactly one of cron or interval")


def _enqueue_key(job_id: str) -> str:
    return f"{ENQUEUE_KEY_PREFIX}{job_id}"


def _enqueue_due_job(
    redis: Redis,
    queues: dict[str, Queue],
    job_id: str,
    spec: dict[str, Any],
    now_ts: float,
) -> str:
    queue_name = spec["queue_name"]
    queue = queues.setdefault(queue_name, Queue(queue_name, connection=redis))
    func_path = str(spec["func_path"])
    task = TASK_FUNCTION_MAP[func_path] if func_path in TASK_FUNCTION_MAP else func_path
    job_options = dict(spec.get("job_options") or {})
    kwargs = dict(spec.get("kwargs") or {})
    args = list(spec.get("args", []))
    meta = dict(spec.get("meta") or {})

    if job_meta := job_options.get("meta"):
        # Preserve scheduler dashboard labels where available.
        meta.update(dict(job_meta))
    if args and is_worker_task_payload(args[0]):
        meta["task_submission"] = build_task_submission_meta(args[0])
    # Deterministic enough for queue dedupe while still carrying the logical cron job id.
    due_slot = int(now_ts)
    rq_job_id = f"cron_{job_id}_{due_slot}"

    queue.enqueue_call(
        func=task,
        args=args,
        kwargs=kwargs,
        job_id=rq_job_id,
        meta=meta or None,
    )

    next_ts = compute_next(spec, now_ts)
    with redis.pipeline() as pipeline:
        pipeline.zadd(NEXT_KEY, {job_id: next_ts})
        pipeline.rpush(_enqueue_key(job_id), rq_job_id)
        pipeline.expire(_enqueue_key(job_id), ENQUEUE_KEY_TTL_SECONDS)
        pipeline.execute()
    return rq_job_id


def acquire_leader(redis: Redis, node_id: str, ttl_seconds: int = 10) -> bool:
    return bool(redis.set(LOCK_KEY, node_id, nx=True, ex=ttl_seconds))


def renew_leader(redis: Redis, node_id: str, ttl_seconds: int = 10) -> bool:
    owner = cast(bytes | str | None, _sync_response(redis.get(LOCK_KEY), "redis.get"))
    if owner and _decode(owner, "redis.get") == node_id:
        redis.expire(LOCK_KEY, ttl_seconds)
        return True
    return False


def run_scheduler(
    redis_url: str = "redis://localhost:6379/0",
    node_id: str = "cron-b-1",
    poll_interval_seconds: float = 15.0,
    redis_password: str | None = None,
) -> None:
    redis = Redis.from_url(redis_url, password=redis_password or None, decode_responses=False)
    queues: dict[str, Queue] = {}
    ttl_seconds = int(max(2 * poll_interval_seconds, 30, Config.CRON_POLL_INTERVAL_SECONDS))

    while True:
        # Keep a single active cron scheduler even if multiple cron instances overlap.

        if not acquire_leader(redis, node_id, ttl_seconds=ttl_seconds) and not renew_leader(redis, node_id, ttl_seconds=ttl_seconds):
            time.sleep(poll_interval_seconds)
            continue

        now_ts = time.time()
        specs = _sync_next_index(redis, now_ts)
        due_ids = cast(
            list[bytes | str],
            _sync_response(redis.zrangebyscore(NEXT_KEY, min=0, max=now_ts, start=0, num=100), "redis.zrangebyscore"),
        )

        for raw_job_id in due_ids:
            job_id = _decode(raw_job_id, "redis.zrangebyscore item")

            spec = specs.get(job_id) or _load_spec(redis, job_id)
            if not spec:
                # Spec was removed; drop stale timing entry.
                redis.zrem(NEXT_KEY, job_id)
                continue

            try:
                _enqueue_due_job(redis, queues, job_id, spec, now_ts)
            except Exception:
                # Keep the job alive and retry on next poll cycle.
                redis.zadd(NEXT_KEY, {job_id: now_ts + poll_interval_seconds})
                logger.exception(f"Failed processing scheduled job {job_id}")

        time.sleep(poll_interval_seconds)


def main() -> None:
    run_scheduler(
        redis_url=Config.REDIS_URL,
        node_id=os.getenv("CRON_NODE_ID", "cron-b-1"),
        poll_interval_seconds=Config.CRON_POLL_INTERVAL_SECONDS,
        redis_password=Config.REDIS_PASSWORD,
    )


if __name__ == "__main__":
    main()

import json
import os
import time
from datetime import datetime, timezone
from typing import Any

from croniter import croniter
from redis import Redis
from rq import Queue


DEFS_KEY = "rq:cron:def"  # HASH: job_id -> JSON spec (written by core QueueManager)
NEXT_KEY = "rq:cron:next"  # ZSET: job_id -> next_run_unix_ts
LOCK_KEY = "rq:cron:leader"  # STRING: leader node id

TASK_FUNCTION_MAP = {
    "collector_task": "worker.collectors.collector_tasks.collector_task",
    "bot_task": "worker.bots.bot_tasks.bot_task",
    "cleanup_token_blacklist": "worker.misc.misc_tasks.cleanup_token_blacklist",
}


def _decode(value: bytes | str) -> str:
    return value.decode() if isinstance(value, bytes) else value


def _normalize_spec(spec: dict[str, Any]) -> dict[str, Any] | None:
    queue_name = spec.get("queue_name") or spec.get("queue")
    func_path = spec.get("func_path") or spec.get("func") or spec.get("task")
    if not queue_name or not func_path:
        return None

    normalized = dict(spec)
    normalized["queue_name"] = queue_name
    normalized["func_path"] = func_path
    normalized["args"] = list(spec.get("args") or [])
    normalized["kwargs"] = dict(spec.get("kwargs") or {})
    normalized["job_options"] = dict(spec.get("job_options") or {})
    normalized["meta"] = dict(spec.get("meta") or {})
    return normalized


def _load_spec(redis: Redis, job_id: str) -> dict[str, Any] | None:
    raw_spec = redis.hget(DEFS_KEY, job_id)
    if not raw_spec:
        return None
    parsed = json.loads(_decode(raw_spec))
    return _normalize_spec(parsed)


def _sync_next_index(redis: Redis, base_ts: float) -> dict[str, dict[str, Any]]:
    raw_specs = redis.hgetall(DEFS_KEY)
    specs: dict[str, dict[str, Any]] = {}

    for raw_job_id, raw_spec in raw_specs.items():
        job_id = _decode(raw_job_id)
        parsed = _normalize_spec(json.loads(_decode(raw_spec)))
        if parsed:
            specs[job_id] = parsed

    next_ids = {_decode(raw_id) for raw_id in redis.zrange(NEXT_KEY, 0, -1)}
    spec_ids = set(specs.keys())

    stale_ids = next_ids - spec_ids
    if stale_ids:
        redis.zrem(NEXT_KEY, *stale_ids)

    missing_ids = spec_ids - next_ids
    for job_id in missing_ids:
        next_ts = compute_next(specs[job_id], base_ts)
        redis.zadd(NEXT_KEY, {job_id: next_ts})

    return specs


def compute_next(spec: dict[str, Any], base_ts: float) -> float:
    if spec.get("cron"):
        dt = datetime.fromtimestamp(base_ts, tz=timezone.utc)
        return croniter(spec["cron"], dt).get_next(datetime).timestamp()
    return base_ts + int(spec["interval"])


def acquire_leader(redis: Redis, node_id: str, ttl_seconds: int = 10) -> bool:
    return bool(redis.set(LOCK_KEY, node_id, nx=True, ex=ttl_seconds))


def renew_leader(redis: Redis, node_id: str, ttl_seconds: int = 10) -> bool:
    owner = redis.get(LOCK_KEY)
    if owner == node_id.encode():
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

    while True:
        # Single active scheduler. Keep this if you run multiple B instances.
        if not acquire_leader(redis, node_id) and not renew_leader(redis, node_id):
            time.sleep(poll_interval_seconds)
            continue

        now_ts = time.time()
        specs = _sync_next_index(redis, now_ts)
        due_ids = redis.zrangebyscore(NEXT_KEY, min=0, max=now_ts, start=0, num=100)

        for raw_job_id in due_ids:
            job_id = _decode(raw_job_id)

            spec = specs.get(job_id) or _load_spec(redis, job_id)
            if not spec:
                # Spec was removed; drop stale timing entry.
                redis.zrem(NEXT_KEY, job_id)
                continue

            try:
                queue_name = spec["queue_name"]
                queue = queues.setdefault(queue_name, Queue(queue_name, connection=redis))
                task = TASK_FUNCTION_MAP.get(spec["func_path"], spec["func_path"])
                job_options = dict(spec.get("job_options") or {})
                kwargs = dict(spec.get("kwargs") or {})

                # Preserve scheduler dashboard labels where available.
                if spec.get("meta") and "meta" not in job_options:
                    job_options["meta"] = spec["meta"]

                # Deterministic job id helps dedupe if the loop retries.
                due_slot = int(now_ts)
                rq_job_id = f"cron_{job_id}_{due_slot}"

                queue.enqueue(
                    task,
                    *spec.get("args", []),
                    job_id=rq_job_id,
                    **kwargs,
                    **job_options,
                )

                next_ts = compute_next(spec, now_ts)
                redis.zadd(NEXT_KEY, {job_id: next_ts})
            except Exception as exc:
                # Keep the job alive and retry on next poll cycle.
                redis.zadd(NEXT_KEY, {job_id: now_ts + poll_interval_seconds})
                print(f"[cron_scheduler] Failed processing job {job_id}: {exc}", flush=True)

        time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    run_scheduler(
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        node_id=os.getenv("CRON_NODE_ID", "cron-b-1"),
        poll_interval_seconds=float(os.getenv("CRON_POLL_INTERVAL_SECONDS", "15.0")),
        redis_password=os.getenv("REDIS_PASSWORD"),
    )

import json
import os
import time
from datetime import datetime, timezone
from typing import Any

from croniter import croniter
from redis import Redis
from rq import Queue


DEFS_KEY = "app:cron:defs"  # HASH: job_id -> JSON spec
NEXT_KEY = "app:cron:next"  # ZSET: job_id -> next_run_unix_ts
LOCK_KEY = "app:cron:leader"  # STRING: leader node id


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
    poll_interval_seconds: float = 1.0,
) -> None:
    redis = Redis.from_url(redis_url)
    queues: dict[str, Queue] = {}

    while True:
        # Single active scheduler. Keep this if you run multiple B instances.
        if not acquire_leader(redis, node_id) and not renew_leader(redis, node_id):
            time.sleep(poll_interval_seconds)
            continue

        now_ts = time.time()
        due_ids = redis.zrangebyscore(NEXT_KEY, min=0, max=now_ts, start=0, num=100)

        for raw_job_id in due_ids:
            job_id = raw_job_id.decode() if isinstance(raw_job_id, bytes) else raw_job_id

            # Claim this due slot.
            if redis.zrem(NEXT_KEY, job_id) == 0:
                continue

            raw_spec = redis.hget(DEFS_KEY, job_id)
            if not raw_spec:
                continue

            spec = json.loads(raw_spec)
            queue_name = spec["queue"]
            queue = queues.setdefault(queue_name, Queue(queue_name, connection=redis))

            # Deterministic job id helps dedupe if the loop retries.
            due_slot = int(now_ts)
            rq_job_id = f"cron:{job_id}:{due_slot}"

            queue.enqueue(
                spec["func"],  # dotted path string, e.g. "myapp.tasks.send_report"
                *spec.get("args", []),
                job_id=rq_job_id,
                **spec.get("kwargs", {}),
                **spec.get("job_options", {}),
            )

            next_ts = compute_next(spec, now_ts)
            redis.zadd(NEXT_KEY, {job_id: next_ts})

        time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    run_scheduler(
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        node_id=os.getenv("CRON_NODE_ID", "cron-b-1"),
        poll_interval_seconds=float(os.getenv("CRON_POLL_INTERVAL_SECONDS", "1.0")),
    )

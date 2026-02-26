#!/usr/bin/env python3
"""Show cron scheduler status for the Redis-backed scheduler.

Usage:
    python show_cron_jobs.py

Or using uv:
    uv run python show_cron_jobs.py
"""

from redis import Redis

from worker.config import Config
from worker.log import logger


DEFS_KEY = "rq:cron:def"
NEXT_KEY = "rq:cron:next"
LOCK_KEY = "rq:cron:leader"


def show_cron_status():
    """Display scheduler lock state and cron definition counters."""
    try:
        redis_conn = Redis.from_url(Config.REDIS_URL, password=Config.REDIS_PASSWORD, decode_responses=False)
        logger.info(f"Connecting to Redis: {Config.REDIS_URL}")
        redis_conn.ping()

        leader_raw = redis_conn.get(LOCK_KEY)
        defs_count = redis_conn.hlen(DEFS_KEY)
        next_count = redis_conn.zcard(NEXT_KEY)

        if not leader_raw:
            print("\nNo active cron scheduler leader found.")
            print("Start scheduler with:")
            print("  uv run python -m worker.cron_scheduler")
            print(f"\nDefinitions in Redis: {defs_count}")
            print(f"Next-run entries in Redis: {next_count}")
            return

        leader = leader_raw.decode() if isinstance(leader_raw, bytes) else str(leader_raw)
        print("\nActive cron scheduler leader:")
        print(f"  {leader}")
        print(f"\nDefinitions in Redis: {defs_count}")
        print(f"Next-run entries in Redis: {next_count}")
    except Exception as e:
        logger.exception(f"Failed to fetch cron scheduler status: {e}")


if __name__ == "__main__":
    show_cron_status()

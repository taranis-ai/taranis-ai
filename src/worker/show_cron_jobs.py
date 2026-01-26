#!/usr/bin/env python3
"""Show registered cron schedulers

This script displays all active RQ cron schedulers.

Usage:
    python show_cron_jobs.py

Or using uv:
    uv run python show_cron_jobs.py
"""

from redis import Redis
from rq.cron import CronScheduler

from worker.config import Config
from worker.log import logger


def show_cron_schedulers():
    """Display all active cron schedulers."""
    try:
        # Connect to Redis
        redis_conn = Redis.from_url(Config.REDIS_URL, password=Config.REDIS_PASSWORD, decode_responses=False)

        logger.info(f"Connecting to Redis: {Config.REDIS_URL}")
        redis_conn.ping()

        # Get all active schedulers
        logger.info("Fetching active cron schedulers...")
        schedulers = CronScheduler.all(redis_conn)

        if not schedulers:
            print("\n❌ No active cron schedulers found")
            print("\nMake sure the RQ cron scheduler is running:")
            print("  uv run python start_cron_scheduler.py")
            return

        print(f"\n✅ Found {len(schedulers)} active cron scheduler(s):\n")
        print("=" * 80)

        for scheduler in schedulers:
            print(f"\nScheduler Name: {scheduler.name}")
            print(f"Hostname: {scheduler.hostname}")
            print(f"PID: {scheduler.pid}")
            print(f"Created At: {scheduler.created_at}")
            print(f"Last Heartbeat: {scheduler.last_heartbeat}")
            if hasattr(scheduler, "config_file") and scheduler.config_file:
                print(f"Config File: {scheduler.config_file}")
            print("-" * 80)

        print("\n📝 Note: Individual cron jobs are registered within the scheduler")
        print("   process and are not visible externally. Check the scheduler logs")
        print("   to see which jobs have been registered.")

    except Exception as e:
        logger.exception(f"Failed to fetch cron schedulers: {e}")


if __name__ == "__main__":
    show_cron_schedulers()

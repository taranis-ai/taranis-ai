#!/usr/bin/env python3
"""Start RQ Cron Scheduler

This script starts the RQ cron scheduler which monitors the database
and automatically enqueues jobs based on their cron schedules.

The scheduler will:
1. Wait for Core API to be available
2. Load all enabled OSINT sources and bots from the database
3. Register them with RQ's cron scheduler
4. Continuously monitor and enqueue jobs at their scheduled times

Usage:
    python start_cron_scheduler.py

Or using uv:
    uv run python start_cron_scheduler.py
"""

import sys

from redis import Redis
from rq.cron import CronScheduler

from worker.config import Config
from worker.core_api import CoreApi
from worker.log import logger


def wait_for_core_api(max_retries: int = 30, retry_delay: int = 2) -> bool:
    """Wait for Core API to become available.

    Args:
        max_retries: Maximum number of connection attempts
        retry_delay: Seconds to wait between retries

    Returns:
        True if Core API is available, False if max retries exceeded
    """
    core_api = CoreApi()

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Checking Core API availability (attempt {attempt}/{max_retries})...")
            # Try to fetch sources - this will fail if Core is not ready
            sources = core_api.get_all_osint_sources()
            if sources is not None:
                logger.info("✓ Core API is available")
                return True
        except Exception as e:
            logger.debug(f"Core API not ready yet: {e}")

        if attempt < max_retries:
            logger.info(f"Waiting {retry_delay}s before next attempt...")
            import time

            time.sleep(retry_delay)

    logger.error(f"Core API did not become available after {max_retries} attempts")
    return False


def start_cron_scheduler():
    """Start the RQ cron scheduler with database-driven configuration."""
    try:
        # Wait for Core API to be available before starting
        if not wait_for_core_api():
            logger.error("Cannot start cron scheduler: Core API is not available")
            sys.exit(1)

        # Connect to Redis
        redis_conn = Redis.from_url(Config.REDIS_URL, password=Config.REDIS_PASSWORD, decode_responses=False)

        logger.info(f"Connecting to Redis: {Config.REDIS_URL}")
        redis_conn.ping()

        # Create the cron scheduler
        # Don't specify a custom name - let RQ auto-generate it in the format "hostname:pid:uuid"
        # This is required for proper registration and monitoring via CronScheduler.all()
        scheduler = CronScheduler(connection=redis_conn, logging_level="INFO")

        logger.info("RQ Cron Scheduler starting...")
        logger.info("Loading cron jobs from database...")

        # Load and register cron jobs with this scheduler instance
        from worker.cron_config import load_cron_jobs

        load_cron_jobs(scheduler)

        logger.info("Cron jobs registered. Starting scheduler loop...")

        # Start the reload listener (pub/sub)
        from worker.cron_reloader import CronReloader

        reloader = CronReloader(scheduler, redis_conn)
        reloader.start()
        logger.info("Cron reloader active - listening for config changes")

        logger.info("Press Ctrl+C to stop")

        # Start the scheduler (this will block and run until interrupted)
        try:
            scheduler.start()
        finally:
            # Stop the reloader when scheduler stops
            reloader.stop()

    except KeyboardInterrupt:
        logger.info("Shutting down cron scheduler...")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Failed to start cron scheduler: {e}")
        sys.exit(1)


if __name__ == "__main__":
    start_cron_scheduler()

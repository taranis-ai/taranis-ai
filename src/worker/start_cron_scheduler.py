#!/usr/bin/env python3
"""Start RQ Cron Scheduler

This script starts the RQ cron scheduler which monitors the database
and automatically enqueues jobs based on their cron schedules.

The scheduler will:
1. Load all enabled OSINT sources and bots from the database
2. Register them with RQ's cron scheduler
3. Continuously monitor and enqueue jobs at their scheduled times

Usage:
    python start_cron_scheduler.py
    
Or using uv:
    uv run python start_cron_scheduler.py
"""
import sys
from redis import Redis
from rq.cron import CronScheduler

from worker.config import Config
from worker.log import logger


def start_cron_scheduler():
    """Start the RQ cron scheduler with database-driven configuration."""
    try:
        # Connect to Redis
        redis_conn = Redis.from_url(
            Config.REDIS_URL,
            password=Config.REDIS_PASSWORD,
            decode_responses=False
        )
        
        logger.info(f"Connecting to Redis: {Config.REDIS_URL}")
        redis_conn.ping()
        
        # Create the cron scheduler
        # Don't specify a custom name - let RQ auto-generate it in the format "hostname:pid:uuid"
        # This is required for proper registration and monitoring via CronScheduler.all()
        scheduler = CronScheduler(
            connection=redis_conn,
            logging_level="INFO"
        )
        
        logger.info("RQ Cron Scheduler starting...")
        logger.info("Loading cron jobs from database...")
        
        # Load and register cron jobs with this scheduler instance
        from worker.cron_config import load_cron_jobs
        load_cron_jobs(scheduler)
        
        logger.info("Cron jobs registered. Starting scheduler loop...")
        logger.info("Press Ctrl+C to stop")
        
        # Start the scheduler (this will block and run until interrupted)
        scheduler.start()
        
    except KeyboardInterrupt:
        logger.info("Shutting down cron scheduler...")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Failed to start cron scheduler: {e}")
        sys.exit(1)


if __name__ == "__main__":
    start_cron_scheduler()


"""RQ Cron Configuration

This module dynamically registers cron jobs from the Core API.
It's used by `rq cron` to schedule recurring tasks.

The scheduler monitors the Core API for changes and reloads jobs when needed.
"""

from rq.cron import register as global_register

from worker.bots.bot_tasks import bot_task
from worker.collectors.collector_tasks import collector_task
from worker.core_api import CoreApi
from worker.log import logger
from worker.misc.misc_tasks import cleanup_token_blacklist


# Task function mapping - maps task names from API to actual task functions
TASK_FUNCTION_MAP = {
    "collector_task": collector_task,
    "bot_task": bot_task,
    "cleanup_token_blacklist": cleanup_token_blacklist,
}


def load_cron_jobs(scheduler=None):
    """Load and register all enabled cron jobs from the Core API.

    Args:
        scheduler: Optional CronScheduler instance. If None, uses global register().

    This function:
    1. Fetches all cron job configurations from Core API
    2. Registers them with RQ's cron scheduler

    This function is called:
    - On startup by rq cron (scheduler=None, uses global register)
    - By start_cron_scheduler.py (scheduler=CronScheduler instance)
    - Periodically to pick up changes (via reload mechanism)
    """
    # Determine which register function to use
    register_func = scheduler.register if scheduler else global_register

    core_api = CoreApi()
    registered_count = 0

    try:
        cron_jobs = core_api.get_cron_jobs()
        if not cron_jobs:
            logger.warning("No cron jobs returned from Core API")
            return

        for job_config in cron_jobs:
            task_name = job_config.get("task")
            queue_name = job_config.get("queue")
            args = job_config.get("args", [])
            cron_schedule = job_config.get("cron")
            task_id = job_config.get("task_id", "unknown")
            job_name = job_config.get("name", "Unknown")

            # Get the task function from the mapping
            task_func = TASK_FUNCTION_MAP.get(task_name)
            if not task_func:
                logger.warning(f"Unknown task function: {task_name}")
                continue

            logger.info(f"Registering cron job: {job_name} ({task_id}) with schedule: {cron_schedule}")

            register_func(
                task_func,
                queue_name=queue_name,
                args=tuple(args),
                cron=cron_schedule,
            )
            registered_count += 1

        logger.info(f"Registered {registered_count} cron jobs from Core API")

    except Exception as e:
        logger.exception(f"Failed to load cron jobs from Core API: {e}")
        raise


# Load jobs on module import (when used with `rq cron config_file.py`)
load_cron_jobs()

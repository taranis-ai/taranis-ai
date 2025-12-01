"""RQ Cron Configuration

This module dynamically registers cron jobs from the database.
It's used by `rq cron` to schedule recurring tasks.

The scheduler monitors the database for changes and reloads jobs when needed.
"""
from rq.cron import register as global_register
from worker.core_api import CoreApi
from worker.log import logger
from worker.collectors.collector_tasks import collector_task
from worker.bots.bot_tasks import bot_task
from worker.misc.misc_tasks import cleanup_token_blacklist


def load_cron_jobs(scheduler=None):
    """Load and register all enabled cron jobs from the database.

    Args:
        scheduler: Optional CronScheduler instance. If None, uses global register().

    This function:
    1. Fetches all enabled OSINT sources with schedules from Core API
    2. Fetches all enabled bots with schedules from Core API
    3. Registers them with RQ's cron scheduler

    This function is called:
    - On startup by rq cron (scheduler=None, uses global register)
    - By start_cron_scheduler.py (scheduler=CronScheduler instance)
    - Periodically to pick up database changes (via reload mechanism)
    """
    # Determine which register function to use
    register_func = scheduler.register if scheduler else global_register

    core_api = CoreApi()
    registered_count = 0

    try:
        # Register OSINT source collectors
        sources = core_api.get_all_osint_sources()
        if sources:
            for source in sources:
                if not source.get('enabled'):
                    continue

                cron_schedule = source.get('refresh')
                if not cron_schedule:
                    continue

                source_id = source.get('id')
                source_type = source.get('type')
                source_name = source.get('name', 'Unknown')

                # Generate task_id matching the format used by core
                task_id = f"collect_{source_type}_{source_id}"

                logger.info(f"Registering collector cron job: {source_name} ({task_id}) with schedule: {cron_schedule}")

                register_func(
                    collector_task,
                    queue_name='collectors',
                    args=(source_id, False),  # manual=False for scheduled jobs
                    cron=cron_schedule,
                )
                registered_count += 1

        # Register Bot tasks
        bots = core_api.get_all_bots()
        if bots:
            for bot in bots:
                if not bot.get('enabled'):
                    continue

                # Bot refresh schedule is in parameters.REFRESH_INTERVAL
                parameters = bot.get('parameters', {})
                cron_schedule = parameters.get('REFRESH_INTERVAL')
                if not cron_schedule:
                    continue

                bot_id = bot.get('id')
                bot_name = bot.get('name', 'Unknown')
                task_id = f"bot_{bot_id}"

                logger.info(f"Registering bot cron job: {bot_name} ({task_id}) with schedule: {cron_schedule}")

                register_func(
                    bot_task,
                    queue_name='bots',
                    args=(bot_id,),
                    cron=cron_schedule,
                )
                registered_count += 1

        # Register housekeeping cron jobs
        logger.info("Registering housekeeping cron job: cleanup_token_blacklist (0 2 * * *)")
        register_func(
            cleanup_token_blacklist,
            queue_name='misc',
            cron='0 2 * * *',
        )
        registered_count += 1

        logger.info(f"Registered {registered_count} cron jobs from database")

    except Exception as e:
        logger.exception(f"Failed to load cron jobs from database: {e}")
        raise


# Load jobs on module import (when used with `rq cron config_file.py`)
load_cron_jobs()

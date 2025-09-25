from datetime import datetime, timedelta
from typing import Any

from core.log import logger
from core.config import Config


cleanup_blacklist_periodic_task = {
    "id": "cleanup_token_blacklist",
    "name": "Cleanup token blacklist",
    "cron": "0 2 * * *",
    "flow_name": "cleanup-blacklist-flow",
}

schedule: "Scheduler | None" = None


class Scheduler:
    def __init__(self):
        self._prefect_client = None
        self._scheduled_tasks: dict[str, dict] = {}
        self.jobs = self._scheduled_tasks
        self.deployments = {}
        self.get_client = lambda: self._prefect_client

    def start(self):
        if Config.DISABLE_SCHEDULER:
            logger.info("Scheduler is disabled")
            return
        logger.info("Prefect scheduler initialized")

    def add_prefect_task(self, task: dict):
        """Convert task definition to Prefect schedule"""
        task_id = task.get("id")
        if not task_id:
            logger.error("Task missing ID, cannot schedule")
            return False

        # Extract cron schedule from APScheduler trigger
        cron_expr = None
        if "jobs_params" in task and "trigger" in task["jobs_params"]:
            trigger = task["jobs_params"]["trigger"]
            if hasattr(trigger, 'fields'):
                # Convert APScheduler CronTrigger to cron expression
                fields = trigger.fields
                cron_expr = f"{fields[5].expressions[0]} {fields[2].expressions[0]} {fields[3].expressions[0]} {fields[4].expressions[0]} {fields[6].expressions[0]}"

        # For OSINT source tasks, extract flow name from celery config
        flow_name = "collector-task-flow"  # Default for collector tasks
        if "celery" in task:
            celery_name = task["celery"].get("name", "")
            if "collector" in celery_name:
                flow_name = "collector-task-flow"
            elif "bot" in celery_name:
                flow_name = "bot-task-flow"

        # Store the task for Prefect scheduling
        prefect_task = {
            "id": task_id,
            "name": task.get("name", task_id),
            "flow_name": flow_name,
            "cron": cron_expr,
            "args": task.get("celery", {}).get("args", []),
            "enabled": True
        }

        self._scheduled_tasks[task_id] = prefect_task

        # For now, we don't create actual Prefect schedules - just store the task info
        # In a full implementation, this would create a Prefect deployment with a schedule
        return True
        logger.info(f"Prefect task '{task_id}' scheduled with cron: {cron_expr}")

    @property
    def scheduler(self):
        return self

    def add_job(self, **kwargs):
        """Add job directly - kept for compatibility but uses Prefect patterns"""
        job_id = kwargs.get('id', 'unknown')
        logger.info(f"Prefect job '{job_id}' would be scheduled with Prefect deployment")

    def get_jobs(self) -> list[dict]:
        """Return scheduled tasks in APScheduler job format for compatibility"""
        return [self._task_to_job_format(task) for task in self._scheduled_tasks.values()]

    def get_job(self, job_id: str) -> dict | None:
        """Get specific job by ID"""
        task = self._scheduled_tasks.get(job_id)
        return self._task_to_job_format(task) if task else None

    def get_periodic_tasks(self) -> dict:
        """Get all periodic tasks"""
        jobs = self.get_jobs()
        return {"items": jobs, "total_count": len(jobs)}

    def get_periodic_task(self, job_id: str) -> dict | None:
        """Get specific periodic task"""
        return self.get_job(job_id)

    def remove_all_jobs(self):
        """Remove all scheduled tasks"""
        self._scheduled_tasks.clear()
        self.jobs.clear()
        logger.info("All Prefect tasks cleared")

    def remove_periodic_task(self, job_id: str) -> bool:
        """Remove a specific periodic task"""
        if job_id in self._scheduled_tasks:
            del self._scheduled_tasks[job_id]
            logger.info(f"Prefect task '{job_id}' removed")
            return True
        logger.warning(f"Prefect task '{job_id}' not found")
        return False

    def _task_to_job_format(self, task: dict) -> dict:
        """Convert Prefect task to APScheduler job format for compatibility"""
        if not task:
            return {}

        cron_expr = task.get("cron", None)
        return {
            "id": task["id"],
            "trigger": "cron" if cron_expr else "unknown",
            "cron": cron_expr,
            "args": str(task.get("args", [])),
            "kwargs": "{}",
            "name": task["name"],
            "next_run_time": None,  # Would need Prefect API call to get actual next run
        }

    def serialize_job(self, job: Any) -> dict:
        """Serialize job data"""
        if isinstance(job, dict):
            return job
        return {"id": "unknown", "trigger": "unknown", "args": "", "kwargs": "", "name": "unknown", "next_run_time": None}

    @classmethod
    def get_next_n_fire_times_from_cron(cls, cron_expr: str, n: int = 3) -> list[datetime]:
        """Get next n fire times from cron expression - simplified for Prefect"""
        # For now, return mock data - in full implementation would use Prefect's scheduling API
        now = datetime.now()
        fire_times = []
        for i in range(n):
            # Simple mock: add hours for demo purposes
            fire_times.append(now + timedelta(hours=i + 1))
        return fire_times

    def initialize_periodic_tasks(self):
        """Initialize all periodic tasks with Prefect"""
        from core.model.osint_source import OSINTSource
        from core.model.bot import Bot

        OSINTSource.schedule_all_osint_sources()
        Bot.schedule_all_bots()


def initialize():
    """Initialize the Prefect-based scheduler"""
    global schedule
    schedule = Scheduler()

    schedule.remove_all_jobs()
    schedule.initialize_periodic_tasks()

    schedule.add_prefect_task(cleanup_blacklist_periodic_task)
    logger.debug("Prefect scheduler initialized")


def get_client():
    return schedule.get_client() if schedule else None

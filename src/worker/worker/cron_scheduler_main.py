import os

from worker.cron_scheduler import run_scheduler


def main() -> None:
    run_scheduler(
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        node_id=os.getenv("CRON_NODE_ID", "cron-b-1"),
        poll_interval_seconds=float(os.getenv("CRON_POLL_INTERVAL_SECONDS", "15.0")),
        redis_password=os.getenv("REDIS_PASSWORD"),
    )

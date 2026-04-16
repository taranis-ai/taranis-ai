import click
from redis import Redis

from worker.config import Config


CRON_LEADER_KEY = "rq:cron:leader"
WORKER_QUEUE_NAMES = {
    "Bots": "bots",
    "Collectors": "collectors",
    "Presenters": "presenters",
    "Publishers": "publishers",
    "Connectors": "connectors",
    "Misc": "misc",
}


def _redis_connection() -> Redis:
    return Redis.from_url(
        Config.REDIS_URL,
        password=Config.REDIS_PASSWORD or None,
        decode_responses=True,
    )


def _expected_worker_queues() -> set[str]:
    return {WORKER_QUEUE_NAMES[worker_type] for worker_type in Config.WORKER_TYPES if worker_type in WORKER_QUEUE_NAMES}


def check_worker_health(redis_connection: Redis, hostname: str | None = None) -> None:
    redis_connection.ping()

    del hostname

    expected_queues = _expected_worker_queues()
    worker_key_pattern = "rq:worker:*"
    for worker_key in redis_connection.scan_iter(match=worker_key_pattern, count=50):
        worker_data = redis_connection.hgetall(worker_key)
        worker_queues = {queue.strip() for queue in worker_data.get("queues", "").split(",") if queue.strip()}
        if worker_queues.intersection(expected_queues):
            return

    raise RuntimeError(f"no active worker found for queues: {', '.join(sorted(expected_queues))}")


def check_cron_health(redis_connection: Redis) -> None:
    redis_connection.ping()

    if redis_connection.get(CRON_LEADER_KEY) is None:
        raise RuntimeError("cron leader lock is missing")


@click.command()
@click.option("--mode", type=click.Choice(("worker", "cron")), required=True, help="Healthcheck mode.")
def main(mode: str) -> None:
    try:
        redis_connection = _redis_connection()
        if mode == "cron":
            check_cron_health(redis_connection)
        else:
            check_worker_health(redis_connection)
    except Exception as exc:
        click.echo(f"worker healthcheck failed: {exc}", err=True)
        raise click.exceptions.Exit(1) from exc

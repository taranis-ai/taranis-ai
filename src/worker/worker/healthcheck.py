import socket

import click
from redis import Redis

from worker.config import Config


CRON_LEADER_KEY = "rq:cron:leader"


def _redis_connection() -> Redis:
    return Redis.from_url(
        Config.REDIS_URL,
        password=Config.REDIS_PASSWORD or None,
        decode_responses=True,
    )


def check_worker_health(redis_connection: Redis, hostname: str | None = None) -> None:
    redis_connection.ping()

    local_hostname = hostname or socket.gethostname()
    worker_key_pattern = f"rq:worker:{local_hostname}.*"
    worker_key = next(redis_connection.scan_iter(match=worker_key_pattern, count=1), None)
    if worker_key is None:
        raise RuntimeError(f"no worker key found for host '{local_hostname}'")


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

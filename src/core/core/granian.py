#!/usr/bin/env python

import os
import time
import multiprocessing
from granian.cli import cli
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from core import create_app
from core.config import Config


def wait_for_db(max_retries=5):
    db_url = Config.SQLALCHEMY_DATABASE_URI
    if not db_url:
        raise RuntimeError("SQLALCHEMY_DATABASE_URI is not set")
    engine = create_engine(db_url, **Config.SQLALCHEMY_ENGINE_OPTIONS)
    retry_count = 0
    wait_time = 1  # Start with a 1 second wait

    while retry_count < max_retries:
        try:
            with engine.connect():
                return
        except OperationalError:
            retry_count += 1
            print(f"Attempt {retry_count}: Waiting for database to be ready (wait: {wait_time}s)...")
            time.sleep(wait_time)
            wait_time = min(wait_time + 1, 5)
        finally:
            engine.dispose()

    raise RuntimeError(f"Could not connect to the database after {max_retries} attempts.")


def app_loader(target):
    if target != "core":
        raise RuntimeError("Should never get there")
    return create_app(initial_setup=False)


def main():
    print("Starting Taranis AI")
    wait_for_db()
    create_app(db_setup=True)
    os.environ["GRANIAN_WORKERS"] = str(os.getenv("GRANIAN_WORKERS", multiprocessing.cpu_count()))
    cli(["--interface", "wsgi", "--factory", "core:granian_app"], auto_envvar_prefix="GRANIAN")


if __name__ == "__main__":
    main()

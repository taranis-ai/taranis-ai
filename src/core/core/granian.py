#!/usr/bin/env python

import os
import time
import multiprocessing
from granian import Granian
from granian.constants import Interfaces
from granian.log import LogLevels
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from core import create_app
from core.config import Config

loglevel = LogLevels.info
if os.getenv("DEBUG", "false").lower() == "true":
    loglevel = LogLevels.debug

workers = int(os.getenv("GRANIAN_WORKERS", multiprocessing.cpu_count()))
address = os.getenv("GRANIAN_ADDRESS", "0.0.0.0")
port = int(os.getenv("GRANIAN_PORT", 8080))


def wait_for_db(max_retries=5):
    db_url = Config.SQLALCHEMY_DATABASE_URI
    if not db_url:
        raise RuntimeError("SQLALCHEMY_DATABASE_URI is not set")
    engine = create_engine(db_url)
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

    raise RuntimeError(f"Could not connect to the database after {max_retries} attempts.")


def app_loader(target):
    if target != "core":
        raise RuntimeError("Should never get there")
    return create_app(initial_setup=False)


def main():
    wait_for_db()
    create_app(initial_setup=True)
    Granian("core", interface=Interfaces.WSGI, address=address, port=port, log_level=loglevel, workers=workers).serve(
        target_loader=app_loader
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python

import os
import time
import multiprocessing
from granian.server import Server as Granian
from granian.constants import Interfaces
from granian.log import LogLevels
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from core import create_app
from core.config import Config
from core.managers.db_seed_manager import sync_enums
from core.managers.db_manager import is_db_empty

loglevel = LogLevels.info
log_access = False
if os.getenv("DEBUG", "false").lower() == "true":
    loglevel = LogLevels.debug
    log_access = True

workers = int(os.getenv("GRANIAN_WORKERS", multiprocessing.cpu_count()))
address = os.getenv("GRANIAN_ADDRESS", "0.0.0.0")
port = int(os.getenv("GRANIAN_PORT", 8080))
connect_timeout = int(os.getenv("SQLALCHEMY_CONNECT_TIMEOUT", 10))


def pre_seed_update_db(engine):
    if not is_db_empty(engine):
        sync_enums(engine)


def wait_for_db(max_retries=5):
    db_url = Config.SQLALCHEMY_DATABASE_URI
    if not db_url:
        raise RuntimeError("SQLALCHEMY_DATABASE_URI is not set")
    engine = create_engine(db_url, connect_args={"connect_timeout": connect_timeout})
    retry_count = 0
    wait_time = 1  # Start with a 1 second wait

    while retry_count < max_retries:
        try:
            with engine.connect():
                pre_seed_update_db(engine)
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
    wait_for_db()
    create_app(db_setup=True)
    Granian("core", interface=Interfaces.WSGI, address=address, port=port, log_level=loglevel, workers=workers, log_access=log_access).serve(
        target_loader=app_loader
    )


if __name__ == "__main__":
    main()

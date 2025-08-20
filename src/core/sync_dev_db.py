import os
import time
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from core import create_app
from core.config import Config
from core.managers.db_seed_manager import sync_enums
from core.managers.db_manager import is_db_empty

CONNECT_TIMEOUT = int(os.getenv("SQLALCHEMY_CONNECT_TIMEOUT", "10"))
MAX_RETRIES = int(os.getenv("DB_MAX_RETRIES", "5"))


def pre_seed_update_db(engine):
    if not is_db_empty(engine):
        sync_enums(engine)


def wait_for_db():
    db_url = Config.SQLALCHEMY_DATABASE_URI
    if not db_url:
        raise RuntimeError("SQLALCHEMY_DATABASE_URI is not set")

    retry = 0
    wait_time = 1
    while retry < MAX_RETRIES:
        engine = create_engine(db_url, connect_args={"connect_timeout": CONNECT_TIMEOUT})
        try:
            with engine.connect():
                pre_seed_update_db(engine)
                return
        except OperationalError:
            retry += 1
            print(f"Attempt {retry}: Waiting for database to be ready (wait: {wait_time}s)...", flush=True)
            time.sleep(wait_time)
            wait_time = min(wait_time + 1, 5)
        finally:
            engine.dispose()
    raise RuntimeError(f"Could not connect to the database after {MAX_RETRIES} attempts.")


if __name__ == "__main__":
    wait_for_db()
    create_app(db_setup=True)

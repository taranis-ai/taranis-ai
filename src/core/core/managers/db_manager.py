from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.engine import reflection, Engine
from sqlalchemy import event
from sqlite3 import Connection as SQLite3Connection

from core.managers.db_seed_manager import pre_seed, pre_seed_update
from core.managers.db_migration_manager import perform_migration
from core.log import logger

db: SQLAlchemy = SQLAlchemy()


def initial_database_setup(engine: Engine):
    is_empty = is_db_empty(engine)
    db.metadata.create_all(bind=engine)
    if is_empty:
        logger.debug("Create new Database")
        pre_seed()
        perform_migration("mark")
    else:
        perform_migration("migrate")
        pre_seed_update(db.engine)

    db.session.remove()


def initialize(app: Flask, initial_setup: bool = True):
    logger.info(f"Connecting Database: {app.config.get('SQLALCHEMY_DATABASE_URI_MASK')}")
    db.init_app(app)

    if initial_setup:
        initial_database_setup(db.engine)
    logger.debug(f"DB Engine created with {db.engine.pool.status()}")


def is_db_empty(engine: Engine) -> bool:
    inspector = reflection.Inspector.from_engine(engine)
    tables = inspector.get_table_names()
    return len(tables) == 0


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

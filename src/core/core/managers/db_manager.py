from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.engine import reflection, Engine
from sqlalchemy import event
from sqlite3 import Connection as SQLite3Connection

from core.managers.db_seed_manager import pre_seed, pre_seed_update
from core.managers.db_migration_manager import migrate, mark
from core.log import logger

db = SQLAlchemy()


def is_db_empty():
    inspector = reflection.Inspector.from_engine(db.engine)
    tables = inspector.get_table_names()
    return len(tables) == 0


def initialize(app, initial_setup: bool = True):
    db.init_app(app)

    if initial_setup:
        logger.info(f"Connecting Database: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
        is_empty = is_db_empty()
        db.create_all()
        if is_empty:
            logger.debug("Create new Database")
            pre_seed()
            mark(app, initial_setup)
        else:
            migrate(app, initial_setup)
            pre_seed_update(db.engine)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

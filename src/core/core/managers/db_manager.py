import sys

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from core.managers.db_seed_manager import pre_seed
from sqlalchemy.engine import reflection
from core.log import logger

from sqlalchemy.engine import Engine
from sqlalchemy import event
from sqlite3 import Connection as SQLite3Connection

db = SQLAlchemy()
migrate = Migrate()


def is_db_empty():
    inspector = reflection.Inspector.from_engine(db.engine)
    tables = inspector.get_table_names()
    return len(tables) == 0


def initialize(app, first_worker):
    db.init_app(app)
    migrate.init_app(app, db)

    if "db" in sys.argv:  # called via flask db
        return

    if not first_worker:
        return

    if is_db_empty():
        logger.debug("Create new Database")
        db.create_all()
        pre_seed(db)
    else:
        logger.debug("Make sure to call: `flask db upgrade`")


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.engine import reflection, Engine
from sqlalchemy import event
from sqlite3 import Connection as SQLite3Connection

from core.managers.db_seed_manager import pre_seed, pre_seed_update, sync_enums
from core.managers.db_migration_manager import perform_migration
from core.log import logger

db: SQLAlchemy = SQLAlchemy()


def initial_database_setup(engine: Engine):
    # Import all models to register them with SQLAlchemy metadata
    # This must be done before calling db.metadata.create_all()
    _import_all_models()

    is_empty = is_db_empty(engine)
    db.metadata.create_all(bind=engine)
    if is_empty:
        logger.debug("Create new Database")
        pre_seed()
        perform_migration("mark")
    else:
        perform_migration("migrate")
        sync_enums(engine)
        pre_seed_update(db.engine)

    db.session.remove()


def _import_all_models():
    """Import all model modules to register them with SQLAlchemy metadata."""
    # Import models individually to avoid circular import issues
    # Import core models first (dependencies for others)
    from core.model import user  # noqa: F401
    from core.model import role  # noqa: F401
    from core.model import permission  # noqa: F401
    from core.model import organization  # noqa: F401
    from core.model import attribute  # noqa: F401
    from core.model import role_based_access  # noqa: F401

    # Import source and collection models
    from core.model import bot  # noqa: F401
    from core.model import osint_source  # noqa: F401
    from core.model import parameter_value  # noqa: F401
    from core.model import connector  # noqa: F401
    from core.model import worker  # noqa: F401
    from core.model import task  # noqa: F401

    # Import news item models
    from core.model import news_item  # noqa: F401
    from core.model import news_item_attribute  # noqa: F401
    from core.model import news_item_tag  # noqa: F401
    from core.model import news_item_conflict  # noqa: F401

    from core.model import story_news_item_attribute  # ✅ add this line

    # Import story models
    from core.model import story  # noqa: F401
    from core.model import story_conflict  # noqa: F401

    # Import report models
    from core.model import report_item_type  # noqa: F401
    from core.model import report_item  # noqa: F401

    # Import product models
    from core.model import product_type  # noqa: F401
    from core.model import product  # noqa: F401
    from core.model import publisher_preset  # noqa: F401

    # Import utility models
    from core.model import word_list  # noqa: F401
    from core.model import asset  # noqa: F401
    from core.model import token_blacklist  # noqa: F401
    from core.model import settings  # noqa: F401


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

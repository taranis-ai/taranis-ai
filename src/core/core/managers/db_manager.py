from sqlite3 import Connection as SQLite3Connection

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, text
from sqlalchemy.engine import Engine, reflection
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import StaticPool

from core.log import logger
from core.managers.db_migration_manager import perform_migration
from core.managers.db_seed_manager import pre_seed, pre_seed_update, sync_enums


db: SQLAlchemy = SQLAlchemy()


def initial_database_setup(engine: Engine):
    is_empty = is_db_empty(engine)
    db.metadata.create_all(bind=engine)
    setup_fts(engine)
    if is_empty:
        logger.debug("Create new Database")
        pre_seed()
        _release_db_connections_for_migration(engine)
        if _supports_migration_backend(engine):
            perform_migration("mark")
    else:
        _release_db_connections_for_migration(engine)
        if _supports_migration_backend(engine):
            perform_migration("migrate")
        sync_enums(engine)
        pre_seed_update(db.engine)

    db.session.remove()


def initialize(app: Flask, initial_setup: bool = True):
    logger.info(f"Connecting Database: {app.config.get('SQLALCHEMY_DATABASE_URI_MASK')}")
    db.init_app(app)

    if initial_setup:
        initial_database_setup(db.engine)
    logger.debug(f"DB Engine created with {db.engine.pool.status()}")


def _release_db_connections_for_migration(engine: Engine) -> None:
    db.session.remove()
    if isinstance(engine.pool, StaticPool):
        return
    engine.dispose()


def _supports_migration_backend(engine: Engine) -> bool:
    if isinstance(engine.pool, StaticPool):
        logger.debug("Skipping yoyo migration backend for single-connection StaticPool engine")
        return False
    return True


def setup_fts(engine: Engine):
    if db.engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        _ensure_unaccent(conn)
        _ensure_pg_trgm(conn)
        with open("core/sql/fulltext_search.sql", "r") as sql_file:
            conn.execute(text(sql_file.read()))


def _ensure_unaccent(connection) -> None:
    try:
        with connection.begin_nested():
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
    except DBAPIError as exc:
        logger.warning(f"Unable to enable unaccent extension; using fallback SQL function instead: {exc}")
        connection.execute(
            text(
                """
                CREATE OR REPLACE FUNCTION unaccent(text)
                RETURNS text
                LANGUAGE sql
                IMMUTABLE
                PARALLEL SAFE
                AS $$ SELECT $1 $$;
                """
            )
        )


def _ensure_pg_trgm(connection) -> None:
    try:
        with connection.begin_nested():
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    except DBAPIError as exc:
        logger.warning(f"Unable to enable pg_trgm extension; continuing without it: {exc}")


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

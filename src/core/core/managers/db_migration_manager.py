from yoyo import read_migrations
from yoyo import get_backend
from core.log import logger


def is_postgresql(uri: str) -> bool:
    return "postgresql" in uri


def migrate(app, initial_setup: bool = True):
    if initial_setup and is_postgresql(app.config.get("SQLALCHEMY_DATABASE_URI")):
        logger.info(f"Migrating Database: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
        backend = get_backend(app.config.get("SQLALCHEMY_DATABASE_URI"))
        migrations = read_migrations("migrations")

        with backend.lock():
            backend.apply_migrations(backend.to_apply(migrations))


def mark(app, initial_setup: bool = True):
    if initial_setup:
        logger.info(f"Marking Database: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
        backend = get_backend(app.config.get("SQLALCHEMY_DATABASE_URI"))
        migrations = read_migrations("migrations")

        with backend.lock():
            backend.mark_migrations(migrations)

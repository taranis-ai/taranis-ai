from yoyo import read_migrations
from yoyo import get_backend
from core.log import logger


def migrate(app, initial_setup: bool = True):
    if initial_setup:
        logger.info(f"Migrating Database: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
        backend = get_backend(app.config.get("SQLALCHEMY_DATABASE_URI"))
        migrations = read_migrations("migrations")

        with backend.lock():
            backend.apply_migrations(backend.to_apply(migrations))

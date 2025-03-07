from yoyo import read_migrations
from yoyo import get_backend
from core.log import logger
from core.config import Config
from typing import Literal


def is_postgresql(uri: str) -> bool:
    return "postgresql" in uri


def perform_migration(action: Literal["migrate", "mark"]):
    if not is_postgresql(Config.SQLALCHEMY_DATABASE_URI):
        return

    logger.info(f"{action.capitalize()}ing Database: {Config.SQLALCHEMY_DATABASE_URI_MASK}")
    backend = get_backend(Config.SQLALCHEMY_DATABASE_URI)
    migrations = read_migrations("migrations")

    with backend.lock():
        if action == "migrate":
            backend.apply_migrations(backend.to_apply(migrations))
            logger.info("Database migrations applied successfully.")
        elif action == "mark":
            backend.mark_migrations(migrations)
            logger.info("Migrations marked successfully.")

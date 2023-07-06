import sys
import subprocess

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade, stamp
from core.managers.db_seed_manager import pre_seed
from sqlalchemy.engine import reflection
from core.managers.log_manager import logger


db = SQLAlchemy()
migrate = Migrate()


def is_db_empty():
    inspector = reflection.Inspector.from_engine(db.engine)
    tables = inspector.get_table_names()
    return len(tables) == 0


def flask_migrate_subprocess(migrate_command):
    result = subprocess.run(["flask", "db", migrate_command], stderr=subprocess.PIPE)
    [logger.debug(line) for line in result.stderr.decode().split("\n") if line]


def initialize(app):
    db.init_app(app)
    migrate.init_app(app, db)

    if "db" in sys.argv:
        return

    if is_db_empty():
        db.create_all()
        flask_migrate_subprocess("stamp")  # stamp(migrate.directory, "head")
        pre_seed(db)
    else:
        flask_migrate_subprocess("upgrade")  # upgrade(migrate.directory, "head")

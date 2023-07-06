from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade, stamp
from core.managers.db_seed_manager import pre_seed
from sqlalchemy.engine import reflection


db = SQLAlchemy()
migrate = Migrate()


def is_db_empty():
    inspector = reflection.Inspector.from_engine(db.engine)
    tables = inspector.get_table_names()
    return len(tables) == 0


def initialize(app):
    db.init_app(app)
    migrate.init_app(app, db)

    if is_db_empty():
        db.create_all()
        stamp(migrate.directory, "head")
    else:
        print("Please call `flask db upgrade` for database migrations")

    pre_seed(db)

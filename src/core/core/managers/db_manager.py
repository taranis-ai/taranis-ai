from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from core.managers.db_seed_manager import pre_seed


db = SQLAlchemy()
migrate = Migrate()


def initialize(app):
    db.init_app(app)
    migrate.init_app(app, db)
    db.create_all(app=app)
    pre_seed(app)

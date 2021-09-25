from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def initialize(app):
    db.init_app(app)


def create_tables():
    db.create_all()

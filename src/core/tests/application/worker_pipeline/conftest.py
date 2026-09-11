import os
import uuid

import pytest
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateSchema, DropSchema

from core.managers.db_manager import db


@pytest.fixture
def postgres_fuzzy_app(app):
    """Exercise PostgreSQL in an isolated schema on an explicitly supplied test database."""
    uri = os.environ.get("TARANIS_TEST_POSTGRES_URI")
    if not uri:
        pytest.skip("Set TARANIS_TEST_POSTGRES_URI to run PostgreSQL migration/concurrency coverage")
    engine = create_engine(uri)
    schema = f"fuzzy_test_{uuid.uuid4().hex}"
    with engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    postgres_app = Flask(__name__)
    postgres_app.config["SQLALCHEMY_DATABASE_URI"] = (
        make_url(uri).update_query_dict({"options": f"-csearch_path={schema}"}).render_as_string(hide_password=False)
    )
    db.init_app(postgres_app)
    try:
        with postgres_app.app_context():
            db.create_all()
        yield postgres_app
    finally:
        with postgres_app.app_context():
            db.session.remove()
            db.engine.dispose()
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        engine.dispose()

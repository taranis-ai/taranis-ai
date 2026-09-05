import logging

import pytest
from flask import Flask
from psycopg.errors import ForeignKeyViolation, NotNullViolation, UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from core.api.config import build_config_blueprint
from core.managers.db_manager import db
from core.model.organization import Organization


@pytest.mark.parametrize("blueprint_name", ["config", "admin"])
@pytest.mark.parametrize(
    ("driver_error", "status", "message"),
    [
        (UniqueViolation("private detail", info={110: b"user_username_key"}), 400, "A record with this field: 'username' already exists."),
        (UniqueViolation("private detail"), 400, "A record with these values already exists."),
        (
            NotNullViolation("private detail", info={99: b"product_type_id", 116: b"product"}),
            400,
            "Cannot set product type id to null because product still requires a value.",
        ),
        (NotNullViolation("private detail", info={99: b"name"}), 400, "A value for name is required."),
        (NotNullViolation("private detail"), 400, "A required value is missing."),
        (ForeignKeyViolation("private detail"), 500, "Database integrity error."),
    ],
)
def test_config_integrity_boundary(blueprint_name, driver_error, status, message, caplog):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    db.init_app(app)
    blueprint = build_config_blueprint(blueprint_name)

    @blueprint.route("/constraint-test", methods=["POST"])
    def fail_constraint():
        db.session.add(Organization(name=None))
        try:
            db.session.commit()
        except IntegrityError as error:
            assert not db.session.is_active
            raise IntegrityError(error.statement, error.params, driver_error) from error
        pytest.fail("Expected a database constraint failure")

    app.register_blueprint(blueprint)
    with app.app_context(), caplog.at_level(logging.ERROR):
        Organization.__table__.create(db.engine)
        response = app.test_client().post(f"{blueprint.url_prefix}/constraint-test")
        assert response.status_code == status
        assert response.json == {"error": message}
        assert db.session.is_active
        assert db.session.execute(select(Organization)).scalars().all() == []
        assert ("Unexpected database integrity failure" in caplog.text) == (status == 500)
        if status == 500:
            assert "private detail" in caplog.text

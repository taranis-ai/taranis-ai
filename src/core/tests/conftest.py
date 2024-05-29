import contextlib
import os
import sys
import pytest
from dotenv import load_dotenv
from sqlalchemy.orm import scoped_session, sessionmaker
from urllib.parse import urlparse

base_dir = os.path.dirname(os.path.abspath(__file__))
env_file = os.path.join(base_dir, ".env")
current_path = os.getcwd()

if not current_path.endswith("src/core"):
    sys.exit("Tests must be run from within src/core")

load_dotenv(dotenv_path=env_file, override=True)


@pytest.fixture(scope="session")
def app():
    from core.__init__ import create_app

    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "DEBUG": True,
            "SERVER_NAME": "localhost",
        }
    )

    yield app

    with contextlib.suppress(Exception):
        parsed_uri = urlparse(os.getenv("SQLALCHEMY_DATABASE_URI"))
        os.remove(f"{parsed_uri.path}")


@pytest.fixture(scope="session")
def client(app):
    yield app.test_client()


@pytest.fixture
def db_persistent_session(app):
    """
    Do not delete the dbsession automatically.
    Use this fixture for debugging the database
    """
    with app.app_context():
        from core.managers.db_manager import db

        yield db.session


@pytest.fixture(scope="session")
def db(app):
    with app.app_context():
        from core.managers.db_manager import db

        yield db

        db.drop_all()


@pytest.fixture
def session(db):
    """Creates a new database session for a test."""
    connection = db.engine.connect()
    transaction = connection.begin()

    db.session = scoped_session(session_factory=sessionmaker(bind=connection))

    yield db.session

    transaction.rollback()
    connection.close()
    db.session.remove()


@pytest.fixture(scope="session")
def access_token(app):
    from flask_jwt_extended import create_access_token
    from core.model.user import User

    with app.app_context():
        return create_access_token(
            identity=User.find_by_name("admin"),
            additional_claims={
                "user_claims": {
                    "id": "admin",
                    "name": "admin",
                    "roles": [1],
                }
            },
        )


@pytest.fixture
def auth_header(access_token):
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-type": "application/json",
    }


@pytest.fixture
def api_header():
    return {"Authorization": "Bearer test_key", "Content-type": "application/json"}


@pytest.fixture(scope="session")
def access_token_user_permissions(app):
    from flask_jwt_extended import create_access_token
    from core.model.user import User

    with app.app_context():
        return create_access_token(
            identity=User.find_by_name("user"),
            additional_claims={
                "user_claims": {
                    "id": "user",
                    "name": "user",
                    "roles": [2],
                }
            },
        )


@pytest.fixture(scope="session")
def access_token_no_permissions(app):
    from flask_jwt_extended import create_access_token

    class FakeUser:
        @property
        def username(self):
            return "nobody"

    nobody = FakeUser()

    with app.app_context():
        return create_access_token(
            identity=nobody,
            additional_claims={
                "user_claims": {
                    "id": "nobody",
                    "name": "nobody",
                    "roles": [],
                }
            },
        )


@pytest.fixture
def clear_blacklist(app):
    from core.model.token_blacklist import TokenBlacklist

    with app.app_context():
        TokenBlacklist.delete_all()


@pytest.fixture
def auth_header_no_permissions(access_token_no_permissions):
    return {
        "Authorization": f"Bearer {access_token_no_permissions}",
        "Content-type": "application/json",
    }


@pytest.fixture
def auth_header_user_permissions(access_token_user_permissions):
    return {
        "Authorization": f"Bearer {access_token_user_permissions}",
        "Content-type": "application/json",
    }


def pytest_addoption(parser):
    group = parser.getgroup("e2e")
    group.addoption("--run-e2e", action="store_const", const="e2e", default=None, help="run e2e tests")
    group.addoption("--run-e2e-ci", action="store_const", const="e2e_ci", default=None, help="run e2e tests for CI")
    group.addoption("--highlight-delay", action="store", default="2", help="delay for highlighting elements in e2e tests")
    group.addoption("--produce-artifacts", action="store_true", default=False, help="create screenshots and record video")


def skip_for_e2e(e2e_test: str, items):
    skip_non_e2e = pytest.mark.skip(reason=f"skip for {e2e_test} test")
    for item in items:
        if e2e_test not in item.keywords:
            item.add_marker(skip_non_e2e)


def pytest_collection_modifyitems(config, items):
    if e2e_type := config.getoption("--run-e2e-ci") or config.getoption("--run-e2e"):
        config.option.start_live_server = False
        config.option.headed = e2e_type == "e2e"
        skip_for_e2e(e2e_type, items)
        return

    for item in items:
        skip_e2e = pytest.mark.skip(reason="need --run-e2e or --run-e2e-ci option to run e2e tests")
        for item in items:
            if "e2e" in item.keywords or "e2e_ci" in item.keywords:
                item.add_marker(skip_e2e)

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

    with contextlib.suppress(Exception):
        parsed_uri = urlparse(os.getenv("SQLALCHEMY_DATABASE_URI"))
        os.remove(f"{parsed_uri.path}")

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
    group.addoption("--e2e-user", action="store_const", const="e2e_user", default=None, help="run e2e tests")
    group.addoption("--e2e-ci", action="store_const", const="e2e_ci", default=None, help="run e2e tests for CI")
    group.addoption("--highlight-delay", action="store", default="2", help="delay for highlighting elements in e2e tests")
    group.addoption("--record-video", action="store_true", default=False, help="create screenshots and record video")
    group.addoption("--e2e-admin", action="store_true", default=False, help="generate documentation screenshots")
    group.addoption("--e2e-user-workflow", action="store_true", default=False, help="run e2e tests for user workflow")


def skip_for_e2e_ci(items):
    skip_non_e2e = pytest.mark.skip(reason="skip for --e2e-ci test")
    for item in items:
        if "e2e_ci" not in item.keywords:
            item.add_marker(skip_non_e2e)


def skip_for_e2e_user(items):
    skip_non_e2e = pytest.mark.skip(reason="skip for --e2e-user test")
    for item in items:
        if "e2e_user" not in item.keywords:
            item.add_marker(skip_non_e2e)


def skip_for_e2e_admin(items):
    skip_non_doc_pictures = pytest.mark.skip(reason="need --e2e-admin option to run tests marked with e2e_admin")
    for item in items:
        if "e2e_admin" not in item.keywords:
            item.add_marker(skip_non_doc_pictures)


def skip_for_e2e_user_workflow(items):
    skip_non_doc_pictures = pytest.mark.skip(reason="need --e2e-user-workflow option to run tests marked with e2e_user_workflow")
    for item in items:
        if "e2e_user_workflow" not in item.keywords:
            item.add_marker(skip_non_doc_pictures)


def pytest_collection_modifyitems(config, items):
    e2e_ci = config.getoption("--e2e-ci")
    e2e_user = config.getoption("--e2e-user")
    e2e_admin = config.getoption("--e2e-admin")
    e2e_user_workflow = config.getoption("--e2e-user-workflow")

    config.option.start_live_server = False
    config.option.headed = True

    if e2e_ci:
        config.option.headed = False
        skip_for_e2e_ci(items)
        return

    if e2e_user:
        skip_for_e2e_user(items)
        return

    if e2e_admin:
        skip_for_e2e_admin(items)
        return

    if e2e_user_workflow:
        skip_for_e2e_user_workflow(items)
        return

    # Skip all e2e and e2e_admin tests if no relevant flag is provided
    skip_all = pytest.mark.skip(reason="need --e2e-user, --e2e-ci, --e2e-user-workflow, or --e2e-admin option to run these tests")
    for item in items:
        if "e2e_user" in item.keywords or "e2e_ci" in item.keywords or "e2e_admin" in item.keywords or "e2e_user_workflow" in item.keywords:
            item.add_marker(skip_all)


@pytest.fixture(scope="session", autouse=True)
def disable_scheduler(app):
    with app.app_context():
        from core.managers.schedule_manager import Scheduler

        Scheduler().shutdown()

    yield

import os
import pytest
from dotenv import load_dotenv

base_dir = os.path.dirname(os.path.abspath(__file__))
env_file = os.path.join(base_dir, ".env")
load_dotenv(dotenv_path=env_file, override=True)


@pytest.fixture(scope="session")
def app():
    from frontend.__init__ import create_app

    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "DEBUG": True,
            "SERVER_NAME": "localhost",
        }
    )

    yield app


@pytest.fixture(scope="session")
def auth_user():
    from frontend.cache import add_user_to_cache

    debug_user = {
        "id": 1,
        "name": "Arthur Dent",
        "organization": {"id": 1, "name": "The Earth"},
        "permissions": [],
        "profile": {},
        "roles": [{"id": 1, "name": "Admin"}],
        "username": "admin",
    }

    yield add_user_to_cache(debug_user)


@pytest.fixture(scope="session")
def access_token(app, auth_user):
    from flask_jwt_extended import create_access_token

    with app.app_context():
        yield create_access_token(identity=auth_user)


@pytest.fixture
def authenticated_client(client, access_token):
    client.set_cookie(
        key="access_token_cookie",
        value=access_token,
    )
    return client


@pytest.fixture(scope="session")
def client(app):
    yield app.test_client()


@pytest.fixture
def htmx_header():
    return {"HX-Request": True}


def pytest_addoption(parser):
    group = parser.getgroup("e2e")
    group.addoption("--e2e-ci", action="store_const", const="e2e_ci", default=None, help="run e2e tests for CI")
    group.addoption("--e2e-timeout", action="store", default="10000", help="milliseconds to wait for e2e tests")
    group.addoption("--highlight-delay", action="store", default="1", help="delay for highlighting elements in e2e tests")
    group.addoption("--record-video", action="store_true", default=False, help="create screenshots and record video")
    group.addoption("--e2e-admin", action="store_true", default=False, help="generate documentation screenshots")


def skip_tests(items, keyword, reason):
    skip_marker = pytest.mark.skip(reason=reason)
    for item in items:
        if keyword not in item.keywords:
            item.add_marker(skip_marker)


def pytest_collection_modifyitems(config, items):
    options = {
        "--e2e-ci": ("e2e_ci", "skip for --e2e-ci test"),
        "--e2e-admin": ("e2e_admin", "need --e2e-admin option to run tests marked with e2e_admin"),
    }

    config.option.start_live_server = False
    config.option.headed = True

    for option, (keyword, reason) in options.items():
        if config.getoption(option):
            if option == "--e2e-ci":
                config.option.headed = False
            skip_tests(items, keyword, reason)
            return

    skip_all = pytest.mark.skip(reason="need --e2e-ci or --e2e-admin option to run these tests")
    for item in items:
        if any(keyword in item.keywords for keyword, _ in options.values()):
            item.add_marker(skip_all)

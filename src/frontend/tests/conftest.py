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

import os
import pytest
from dotenv import load_dotenv

base_dir = os.path.dirname(os.path.abspath(__file__))
env_file = os.path.join(base_dir, ".env")
load_dotenv(dotenv_path=env_file, override=True)


@pytest.fixture(scope="session")
def app():
    from admin.__init__ import create_app

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
    from admin.cache import add_user_to_cache

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
def dashboard_get_mock(requests_mock):
    from admin.config import Config

    mock_data = {
        "latest_collected": "2025-01-14T21:16:42.699574+01:00",
        "report_items_completed": 5,
        "report_items_in_progress": 1,
        "schedule_length": 2,
        "total_database_items": 308,
        "total_news_items": 306,
        "total_products": 1,
    }

    requests_mock.get(f"{Config.TARANIS_CORE_URL}/dashboard", json=mock_data)
    yield mock_data


@pytest.fixture
def users_get_mock(requests_mock):
    from admin.config import Config

    mock_data = {
        "items": [
            {
                "id": 1,
                "name": "Arthur Dent",
                "organization": 1,
                "permissions": [
                    "ASSESS_ACCESS",
                    "ANALYZE_ACCESS",
                    "PUBLISH_PRODUCT",
                    "PUBLISH_ACCESS",
                    "PUBLISH_CREATE",
                    "ASSESS_DELETE",
                    "BOT_EXECUTE",
                    "ANALYZE_DELETE",
                    "ANALYZE_UPDATE",
                    "ASSESS_CREATE",
                ],
                "profile": {},
                "roles": [1],
                "username": "admin",
            },
            {
                "id": 6,
                "name": "ccc",
                "organization": 2,
                "permissions": [
                    "PUBLISH_DELETE",
                    "ASSESS_UPDATE",
                    "ANALYZE_CREATE",
                    "PUBLISH_UPDATE",
                    "ASSESS_ACCESS",
                    "ANALYZE_ACCESS",
                    "PUBLISH_PRODUCT",
                    "PUBLISH_ACCESS",
                    "PUBLISH_CREATE",
                    "ASSESS_DELETE",
                    "BOT_EXECUTE",
                    "ANALYZE_DELETE",
                    "ANALYZE_UPDATE",
                    "ASSESS_CREATE",
                ],
                "profile": {},
                "roles": [2],
                "username": "ccc",
            },
        ],
        "total_count": 2,
    }

    requests_mock.get(f"{Config.TARANIS_CORE_URL}/config/users", json=mock_data)
    yield mock_data

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

    mock_data = [{"id": 1, "name": "admin", "username": "Admin"}]

    requests_mock.get(f"{Config.TARANIS_CORE_URL}/config/users", json=mock_data)
    yield mock_data

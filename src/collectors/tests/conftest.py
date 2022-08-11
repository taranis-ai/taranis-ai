import pytest
from dotenv import load_dotenv

load_dotenv(dotenv_path="tests/.env", override=True)


@pytest.fixture()
def app():
    from collectors.__init__ import create_app

    yield create_app()


@pytest.fixture
def client(app):
    return app.test_client()

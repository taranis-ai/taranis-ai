import pytest
from presenters.__init__ import create_app


@pytest.fixture()
def app():
    yield create_app("tests/.env")


@pytest.fixture
def client(app):
    return app.test_client()

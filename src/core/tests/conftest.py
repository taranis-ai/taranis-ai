import pytest
from dotenv import load_dotenv
# from sqlalchemy import event
# from sqlalchemy.orm import sessionmaker

load_dotenv(dotenv_path="tests/.env", override=True)


@pytest.fixture()
def app():
    from core.__init__ import create_app
    yield create_app()


@pytest.fixture
def client(app):
    yield app.test_client()


@pytest.fixture()
def _db(app):
    with app.app_context():
        from core.managers.db_manager import db
        yield db

@pytest.fixture
def news_item_data(app):
    with app.app_context():
        from core.model.news_item import NewsItemData
        yield NewsItemData


@pytest.fixture
def news_item(app):
    with app.app_context():
        from core.model.news_item import NewsItem
        yield NewsItem


@pytest.fixture
def access_token(app):
    from flask_jwt_extended import create_access_token

    with app.app_context():
        return create_access_token(
            identity="admin",
            additional_claims={
                "user_claims": {
                    "id": "admin",
                    "name": "admin",
                    "organization_name": "TestOrg",
                    "permissions": ["ASSESS_ACCESS", "PUBLISH_ACCESS", "ASSESS_CREATE"],
                }
            },
        )


@pytest.fixture
def auth_header(access_token):
    return {"Authorization": f"Bearer {access_token}", "Content-type": "application/json"}

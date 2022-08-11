import pytest
from dotenv import load_dotenv

load_dotenv(dotenv_path="tests/.env", override=True)


@pytest.fixture()
def app():
    from core.__init__ import create_app

    yield create_app()


@pytest.fixture
def client(app):
    return app.test_client()


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
                    "permissions": ["ASSESS_ACCESS", "PUBLISH_ACCESS"],
                }
            },
        )


@pytest.fixture
def auth_header(access_token):
    return {"Authorization": f"Bearer {access_token}"}

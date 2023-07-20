import pytest
import os
from dotenv import load_dotenv
from sqlalchemy.orm import scoped_session, sessionmaker

# from sqlalchemy import event
# from sqlalchemy.orm import sessionmaker

load_dotenv(dotenv_path="tests/.env", override=True)


@pytest.fixture(scope="session")
def app(request):
    from core.__init__ import create_app

    def teardown():
        os.remove("/var/tmp/taranis_test.db")

    request.addfinalizer(teardown)
    yield create_app()


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
def db(app, request):
    with app.app_context():
        from core.managers.db_manager import db

        def teardown():
            db.drop_all()

        request.addfinalizer(teardown)

        yield db


@pytest.fixture()
def session(db, request):
    """Creates a new database session for a test."""
    connection = db.engine.connect()
    transaction = connection.begin()

    db.session = scoped_session(session_factory=sessionmaker(bind=connection))

    def teardown():
        transaction.rollback()
        connection.close()
        db.session.remove()

    request.addfinalizer(teardown)
    return db.session


@pytest.fixture(scope="session")
def access_token(app, permissions):
    from flask_jwt_extended import create_access_token

    with app.app_context():
        return create_access_token(
            identity="admin",
            additional_claims={
                "user_claims": {
                    "id": "admin",
                    "name": "admin",
                    "organization_name": "TestOrg",
                    "permissions": permissions,
                }
            },
        )


@pytest.fixture
def auth_header(access_token):
    return {"Authorization": f"Bearer {access_token}", "Content-type": "application/json"}


@pytest.fixture(scope="session")
def permissions():
    yield [
        "ASSESS_ACCESS",
        "ASSESS_CREATE",
        "ASSESS_UPDATE",
        "ASSESS_DELETE",
        "ANALYZE_ACCESS",
        "ANALYZE_CREATE",
        "ANALYZE_UPDATE",
        "ANALYZE_DELETE",
        "PUBLISH_ACCESS",
        "PUBLISH_CREATE",
        "PUBLISH_UPDATE",
        "PUBLISH_DELETE",
        "PUBLISH_PRODUCT",
        "MY_ASSETS_ACCESS",
        "MY_ASSETS_CREATE",
        "MY_ASSETS_CONFIG",
        "CONFIG_ACCESS",
        "CONFIG_ORGANIZATION_ACCESS",
        "CONFIG_ORGANIZATION_CREATE",
        "CONFIG_ORGANIZATION_UPDATE",
        "CONFIG_ORGANIZATION_DELETE",
        "CONFIG_USER_ACCESS",
        "CONFIG_USER_CREATE",
        "CONFIG_USER_UPDATE",
        "CONFIG_USER_DELETE",
        "CONFIG_ROLE_ACCESS",
        "CONFIG_ROLE_CREATE",
        "CONFIG_ROLE_UPDATE",
        "CONFIG_ROLE_DELETE",
        "CONFIG_ACL_ACCESS",
        "CONFIG_ACL_CREATE",
        "CONFIG_ACL_UPDATE",
        "CONFIG_ACL_DELETE",
        "CONFIG_ATTRIBUTE_ACCESS",
        "CONFIG_ATTRIBUTE_CREATE",
        "CONFIG_ATTRIBUTE_UPDATE",
        "CONFIG_ATTRIBUTE_DELETE",
        "CONFIG_REPORT_TYPE_ACCESS",
        "CONFIG_REPORT_TYPE_CREATE",
        "CONFIG_REPORT_TYPE_UPDATE",
        "CONFIG_REPORT_TYPE_DELETE",
        "CONFIG_WORD_LIST_ACCESS",
        "CONFIG_WORD_LIST_CREATE",
        "CONFIG_WORD_LIST_UPDATE",
        "CONFIG_WORD_LIST_DELETE",
        "CONFIG_BOTS_NODE_ACCESS",
        "CONFIG_BOTS_NODE_CREATE",
        "CONFIG_BOTS_NODE_UPDATE",
        "CONFIG_BOTS_NODE_DELETE",
        "CONFIG_BOT_PRESET_ACCESS",
        "CONFIG_BOT_PRESET_CREATE",
        "CONFIG_BOT_PRESET_UPDATE",
        "CONFIG_BOT_PRESET_DELETE",
        "CONFIG_OSINT_SOURCE_ACCESS",
        "CONFIG_OSINT_SOURCE_CREATE",
        "CONFIG_OSINT_SOURCE_UPDATE",
        "CONFIG_OSINT_SOURCE_DELETE",
        "CONFIG_OSINT_SOURCE_GROUP_ACCESS",
        "CONFIG_OSINT_SOURCE_GROUP_CREATE",
        "CONFIG_OSINT_SOURCE_GROUP_UPDATE",
        "CONFIG_OSINT_SOURCE_GROUP_DELETE",
        "CONFIG_PRESENTERS_NODE_ACCESS",
        "CONFIG_PRESENTERS_NODE_CREATE",
        "CONFIG_PRESENTERS_NODE_UPDATE",
        "CONFIG_PRESENTERS_NODE_DELETE",
        "CONFIG_PRODUCT_TYPE_ACCESS",
        "CONFIG_PRODUCT_TYPE_CREATE",
        "CONFIG_PRODUCT_TYPE_UPDATE",
        "CONFIG_PRODUCT_TYPE_DELETE",
        "CONFIG_PUBLISHERS_NODE_ACCESS",
        "CONFIG_PUBLISHERS_NODE_CREATE",
        "CONFIG_PUBLISHERS_NODE_UPDATE",
        "CONFIG_PUBLISHERS_NODE_DELETE",
        "CONFIG_PUBLISHER_PRESET_ACCESS",
        "CONFIG_PUBLISHER_PRESET_CREATE",
        "CONFIG_PUBLISHER_PRESET_UPDATE",
        "CONFIG_PUBLISHER_PRESET_DELETE",
        "CONFIG_REMOTE_ACCESS_ACCESS",
        "CONFIG_REMOTE_ACCESS_CREATE",
        "CONFIG_REMOTE_ACCESS_UPDATE",
        "CONFIG_REMOTE_ACCESS_DELETE",
        "CONFIG_REMOTE_NODE_ACCESS",
        "CONFIG_REMOTE_NODE_CREATE",
        "CONFIG_REMOTE_NODE_UPDATE",
        "CONFIG_REMOTE_NODE_DELETE",
        "CONFIG_NODE_ACCESS",
        "CONFIG_WORKER_ACCESS",
        "CONFIG_API_ACCESS",
    ]

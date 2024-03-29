import pytest
from dotenv import load_dotenv
from sqlalchemy.orm import scoped_session, sessionmaker

# from sqlalchemy import event
# from sqlalchemy.orm import sessionmaker

load_dotenv(dotenv_path="tests/.env", override=True)


@pytest.fixture(scope="session")
def app(request):
    from core.__init__ import create_app

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
def access_token(app):
    from flask_jwt_extended import create_access_token

    with app.app_context():
        return create_access_token(
            identity="admin",
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
    return {"Authorization": f"Bearer {access_token}", "Content-type": "application/json"}


@pytest.fixture
def api_header():
    return {"Authorization": "Bearer test_key", "Content-type": "application/json"}


@pytest.fixture(scope="session")
def access_token_user_permissions(app):
    from flask_jwt_extended import create_access_token

    with app.app_context():
        return create_access_token(
            identity="user",
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

    with app.app_context():
        return create_access_token(
            identity="nobody",
            additional_claims={
                "user_claims": {
                    "id": "nobody",
                    "name": "nobody",
                    "roles": [],
                }
            },
        )


@pytest.fixture
def auth_header_no_permissions(access_token_no_permissions):
    return {"Authorization": f"Bearer {access_token_no_permissions}", "Content-type": "application/json"}


@pytest.fixture
def auth_header_user_permissions(access_token_user_permissions):
    return {"Authorization": f"Bearer {access_token_user_permissions}", "Content-type": "application/json"}

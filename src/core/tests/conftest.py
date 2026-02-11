import contextlib
import os
import sys
from urllib.parse import urlparse

import pytest
from dotenv import load_dotenv
from sqlalchemy.orm import scoped_session, sessionmaker


base_dir = os.path.dirname(os.path.abspath(__file__))
env_file = os.path.join(base_dir, ".env")
current_path = os.getcwd()

if not current_path.endswith("src/core"):
    sys.exit("Tests must be run from within src/core")

load_dotenv(dotenv_path=env_file, override=True)


@pytest.fixture(scope="session")
def app():
    from core.__init__ import create_app

    with contextlib.suppress(Exception):
        parsed_uri = urlparse(os.getenv("SQLALCHEMY_DATABASE_URI"))
        os.remove(f"{parsed_uri.path}")

    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "DEBUG": True,
            "SERVER_NAME": "localhost",
        }
    )

    yield app

    with contextlib.suppress(Exception):
        parsed_uri = urlparse(os.getenv("SQLALCHEMY_DATABASE_URI"))
        # os.remove(f"{parsed_uri.path}")


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
def db(app):
    with app.app_context():
        from core.managers.db_manager import db

        yield db

        db.drop_all()


@pytest.fixture
def session(db):
    """Creates a new database session for a test."""
    connection = db.engine.connect()
    transaction = connection.begin()

    db.session = scoped_session(session_factory=sessionmaker(bind=connection))

    yield db.session

    transaction.rollback()
    connection.close()
    db.session.remove()


@pytest.fixture(scope="session")
def access_token(app):
    from flask_jwt_extended import create_access_token

    from core.model.user import User

    with app.app_context():
        return create_access_token(
            identity=User.find_by_name("admin"),
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
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-type": "application/json",
    }


@pytest.fixture
def api_header():
    return {"Authorization": f"Bearer {os.getenv('API_KEY')}", "Content-type": "application/json"}


@pytest.fixture(scope="session")
def access_token_user_permissions(app):
    from flask_jwt_extended import create_access_token

    from core.model.user import User

    with app.app_context():
        return create_access_token(
            identity=User.find_by_name("user"),
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

    class FakeUser:
        @property
        def username(self):
            return "nobody"

    nobody = FakeUser()

    with app.app_context():
        return create_access_token(
            identity=nobody,
            additional_claims={
                "user_claims": {
                    "id": "nobody",
                    "name": "nobody",
                    "roles": [],
                }
            },
        )


@pytest.fixture
def clear_blacklist(app):
    from core.model.token_blacklist import TokenBlacklist

    with app.app_context():
        TokenBlacklist.delete_all()


@pytest.fixture
def auth_header_no_permissions(access_token_no_permissions):
    return {
        "Authorization": f"Bearer {access_token_no_permissions}",
        "Content-type": "application/json",
    }


@pytest.fixture
def auth_header_user_permissions(access_token_user_permissions):
    return {
        "Authorization": f"Bearer {access_token_user_permissions}",
        "Content-type": "application/json",
    }


@pytest.fixture
def auth_bypass(monkeypatch):
    """Bypass auth/permission checks for unit-level API tests."""
    import flask_jwt_extended.utils as jwt_utils

    from core.managers import auth_manager

    monkeypatch.setattr(auth_manager, "verify_jwt_in_request", lambda *a, **k: None)
    monkeypatch.setattr(auth_manager, "get_jwt_identity", lambda: "tester")
    monkeypatch.setattr(jwt_utils, "get_jwt", lambda: {"sub": "tester"})
    monkeypatch.setattr(
        jwt_utils,
        "get_current_user",
        lambda: type("User", (), {"get_permissions": lambda self: {"CONFIG_WORKER_ACCESS"}})(),
    )


def _is_vscode(config) -> bool:
    # Primary: pytest plugin loaded by the VS Code Python extension
    if config.pluginmanager.hasplugin("vscode_pytest"):
        return True
    # Fallbacks (sometimes present when launched from VS Code)
    return bool(os.getenv("VSCODE_PID") or os.getenv("VSCODE_CWD"))


def pytest_addoption(parser):
    group = parser.getgroup("e2e")
    group.addoption("--e2e-user", action="store_const", const="e2e_user", default=None, help="run e2e tests")
    group.addoption("--e2e-ci", action="store_const", const="e2e_ci", default=None, help="run e2e tests for CI")
    group.addoption("--e2e-timeout", action="store", default="10000", help="milliseconds to wait for e2e tests")
    group.addoption("--highlight-delay", action="store", default="2", help="delay for highlighting elements in e2e tests")
    group.addoption("--record-video", action="store_true", default=False, help="create screenshots and record video")
    group.addoption("--e2e-user-workflow", action="store_true", default=False, help="run e2e tests for user workflow")


def skip_tests(items, keyword, reason):
    skip_marker = pytest.mark.skip(reason=reason)
    for item in items:
        if keyword not in item.keywords:
            item.add_marker(skip_marker)


def pytest_collection_modifyitems(config, items):
    config.option.start_live_server = False

    if _is_vscode(config):
        config.option.trace = True
        config.option.headed = False
        return

    options = {
        "--e2e-ci": ("e2e_ci", "skip for --e2e-ci test"),
        "--e2e-user": ("e2e_user", "skip for --e2e-user test"),
        "--e2e-user-workflow": ("e2e_user_workflow", "need --e2e-user-workflow option to run tests marked with e2e_user_workflow"),
    }

    config.option.headed = True

    for option, (keyword, reason) in options.items():
        if config.getoption(option):
            if option == "--e2e-ci":
                config.option.trace = True
                config.option.headed = False
            skip_tests(items, keyword, reason)
            return

    skip_all = pytest.mark.skip(reason="need --e2e-user, --e2e-ci, --e2e-user-workflow option to run these tests")
    for item in items:
        if any(keyword in item.keywords for keyword, _ in options.values()):
            item.add_marker(skip_all)


@pytest.fixture
def sample_report_type(app):
    """Create a sample ReportItemType for testing"""
    with app.app_context():
        from core.managers.db_manager import db
        from core.model.report_item_type import ReportItemType

        report_type = ReportItemType(title="Test Report Type", description="A test report type for cascade testing")
        db.session.add(report_type)
        db.session.commit()
        yield report_type
        # Cleanup
        try:
            db.session.delete(report_type)
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture
def sample_product_type(app, sample_report_type):
    """Create a sample ProductType linked to the ReportItemType"""
    with app.app_context():
        from models.types import PRESENTER_TYPES

        from core.managers.db_manager import db
        from core.model.product_type import ProductType

        product_type = ProductType(
            title="Test Product Type",
            type=PRESENTER_TYPES.HTML_PRESENTER,
            description="A test product type",
            report_types=[sample_report_type.id],
        )
        db.session.add(product_type)
        db.session.commit()
        yield product_type
        # Cleanup
        try:
            db.session.delete(product_type)
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture
def additional_product_type(app, sample_report_type):
    """Create another ProductType linked to the same ReportItemType"""
    with app.app_context():
        from models.types import PRESENTER_TYPES

        from core.managers.db_manager import db
        from core.model.product_type import ProductType

        product_type2 = ProductType(
            title="Second Test Product Type",
            type=PRESENTER_TYPES.PDF_PRESENTER,
            description="A second test product type",
            report_types=[sample_report_type.id],
        )
        db.session.add(product_type2)
        db.session.commit()
        yield product_type2
        # Cleanup
        try:
            db.session.delete(product_type2)
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture
def sample_product_type_multi_report_types(app):
    with app.app_context():
        from models.types import PRESENTER_TYPES

        from core.managers.db_manager import db
        from core.model.product_type import ProductType
        from core.model.report_item_type import ReportItemType

        # Create multiple ReportItemTypes
        report_type1 = ReportItemType(title="Report Type 1", description="First report type")
        report_type2 = ReportItemType(title="Report Type 2", description="Second report type")
        report_type3 = ReportItemType(title="Report Type 3", description="Third report type")

        db.session.add_all([report_type1, report_type2, report_type3])
        db.session.flush()

        # Create a ProductType that references all three ReportItemTypes
        product_type = ProductType(
            title="Multi-Report Product Type",
            type=PRESENTER_TYPES.HTML_PRESENTER,
            description="Product type with multiple report types",
            report_types=[report_type1.id, report_type2.id, report_type3.id],
        )
        db.session.add(product_type)
        db.session.commit()
        yield product_type
        try:
            db.session.delete(product_type)
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture
def osint_sources(app):
    """Create test OSINT sources with schedules"""
    with app.app_context():
        from core.managers.db_manager import db
        from core.model.osint_source import OSINTSource

        source1 = OSINTSource(
            name="Test RSS Source",
            description="RSS collector used in cron job tests",
            type="rss_collector",
            parameters={"feed": "https://example.com/feed", "REFRESH_INTERVAL": "0 * * * *"},
        )
        source1.enabled = True

        source2 = OSINTSource(
            name="Test Web Source",
            description="Web collector used in cron job tests",
            type="simple_web_collector",
            parameters={"url": "https://example.com", "REFRESH_INTERVAL": "*/30 * * * *"},
        )
        source2.enabled = True

        sources = [source1, source2]
        db.session.add_all(sources)
        db.session.commit()
        yield sources
        try:
            for source in sources:
                db.session.delete(source)
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture
def disabled_osint_source(app):
    """Create a disabled OSINT source"""
    with app.app_context():
        from core.managers.db_manager import db
        from core.model.osint_source import OSINTSource

        source = OSINTSource(
            name="Disabled Source",
            description="Disabled collector fixture",
            type="rss_collector",
            parameters={"feed": "https://example.com/disabled", "REFRESH_INTERVAL": "0 * * * *"},
        )
        source.enabled = False
        db.session.add(source)
        db.session.commit()
        yield source
        try:
            db.session.delete(source)
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture
def osint_source_no_schedule(app):
    """Create an OSINT source without a schedule"""
    with app.app_context():
        from core.managers.db_manager import db
        from core.model.osint_source import OSINTSource

        source = OSINTSource(
            name="No Schedule Source",
            description="Collector without schedule for exclusion test",
            type="rss_collector",
            parameters={"feed": "https://example.com/no-schedule", "REFRESH_INTERVAL": ""},  # Empty REFRESH_INTERVAL to skip scheduling
        )
        source.enabled = True
        db.session.add(source)
        db.session.commit()
        yield source
        try:
            db.session.delete(source)
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture
def bots(app):
    """Create test bots with schedules"""
    with app.app_context():
        from core.managers.db_manager import db
        from core.model.bot import Bot

        highest_index = Bot.get_highest_index()

        bot1 = Bot(
            name="Test IOC Bot",
            description="IOC bot fixture for cron job tests",
            type="ioc_bot",
            index=highest_index + 1,
            parameters={"REFRESH_INTERVAL": "0 2 * * *"},  # Daily at 2am
        )
        bot1.enabled = True

        bot2 = Bot(
            name="Test NLP Bot",
            description="NLP bot fixture for cron job tests",
            type="nlp_bot",
            index=highest_index + 2,
            parameters={"REFRESH_INTERVAL": "0 */6 * * *"},  # Every 6 hours
        )
        bot2.enabled = True

        bots = [bot1, bot2]
        db.session.add_all(bots)
        db.session.commit()
        yield bots
        try:
            for bot in bots:
                db.session.delete(bot)
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture
def disabled_bot(app):
    """Create a disabled bot"""
    with app.app_context():
        from core.managers.db_manager import db
        from core.model.bot import Bot

        bot = Bot(
            name="Disabled Bot",
            description="Disabled bot fixture",
            type="ioc_bot",
            parameters={"REFRESH_INTERVAL": "0 * * * *"},
        )
        bot.enabled = False
        db.session.add(bot)
        db.session.commit()
        yield bot
        try:
            db.session.delete(bot)
            db.session.commit()
        except Exception:
            db.session.rollback()

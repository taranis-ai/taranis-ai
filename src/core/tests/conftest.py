import contextlib
import os
import sys
import pytest
from dotenv import load_dotenv
from sqlalchemy.orm import scoped_session, sessionmaker
from urllib.parse import urlparse


base_dir = os.path.dirname(os.path.abspath(__file__))
env_file = os.path.join(base_dir, ".env")
current_path = os.getcwd()

if not current_path.endswith("src/core"):
    sys.exit("Tests must be run from within src/core")

load_dotenv(dotenv_path=env_file, override=True)

print("=== ENV DEBUG START ===")
print("SQLALCHEMY_DATABASE_URI:", os.getenv("SQLALCHEMY_DATABASE_URI"))
print("API_KEY:", os.getenv("API_KEY"))
print("DEBUG:", os.getenv("DEBUG"))
print("SERVER_NAME:", os.getenv("SERVER_NAME"))
print("=== ENV DEBUG END ===")


@pytest.fixture(scope="session")
def logger(app):
    import logging

    # Create a simple test logger that doesn't trigger Config loading
    test_logger = logging.getLogger(__name__)
    test_logger.setLevel(logging.DEBUG)
    return test_logger


@pytest.fixture(scope="session")
def app():
    from core.__init__ import create_app

    with contextlib.suppress(Exception):
        parsed_uri = urlparse(os.getenv("SQLALCHEMY_DATABASE_URI"))
        print(f"Removing test database file: {parsed_uri.path}")
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

        # Clean up all data and drop tables at the end of the session
        try:
            db.session.remove()
            db.drop_all()
        except Exception:
            pass


@pytest.fixture
def session(db):
    """Creates a new database session for a test."""
    from core.managers.history_meta import versioned_session

    connection = db.engine.connect()
    transaction = connection.begin()

    # Store the original session to restore later
    original_session = db.session

    db.session = scoped_session(sessionmaker(bind=connection))

    # Import versioned_session locally to avoid triggering config loading at module level
    try:
        from core.managers.history_meta import versioned_session

        versioned_session(db.session)
        print("Using versioned_session for history tracking @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    except ImportError:
        # Fallback if versioned_session is not available
        print("versioned_session not available, using regular session @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")

    yield db.session

    # Ensure all pending changes are cleared before rollback
    db.session.expunge_all()
    transaction.rollback()
    connection.close()
    db.session.remove()

    # Restore the original session for cleanup fixtures
    db.session = original_session


@pytest.fixture(autouse=True, scope="class")
def clean_db_before_class(app):
    """Automatically clean test data before each test class to prevent conflicts."""
    with app.app_context():
        from core.managers.db_manager import db
        import contextlib
        from sqlalchemy import text

        # Clean only tables that contain test-generated data to prevent unique constraint violations
        # Keep seeded data (users, roles, organizations, report types, etc.) intact
        # Order matters due to foreign key relationships
        tables_to_clean = [
            'report_item_story',      # Junction table first due to foreign keys  
            'story_news_item_attribute',
            'news_item_attribute',
            'report_item_attribute',  # Report attributes
            'report_item_cpe',        # Report CPE data
            'report_item',            # Reports themselves
            'story_search_index',     # Story search index causing duplicate issues
            'news_item_tag',          # News item tags
            'news_item',
            'story'
        ]

        def clean_tables():
            with contextlib.suppress(Exception):
                # Disable foreign key checks temporarily for cleanup
                db.session.execute(text("PRAGMA foreign_keys=OFF"))

                for table_name in tables_to_clean:
                    db.session.execute(text(f"DELETE FROM {table_name}"))

                # Re-enable foreign key checks
                db.session.execute(text("PRAGMA foreign_keys=ON"))

                db.session.commit()

        # Clean before test class
        clean_tables()

        yield

        # Clean up after class too
        clean_tables()


@pytest.fixture(autouse=True, scope="function")
def clean_reports_after_function(app):
    """Clean report data after each test function to prevent contamination within a test class."""
    yield
    
    with app.app_context():
        from core.managers.db_manager import db
        import contextlib
        from sqlalchemy import text
        
        with contextlib.suppress(Exception):
            # Clean report-related tables that can be created during tests
            report_tables = [
                'report_item_story',
                'report_item_attribute',
                'report_item_cpe', 
                'report_item'
            ]
            
            # Disable foreign key checks temporarily for cleanup
            db.session.execute(text("PRAGMA foreign_keys=OFF"))
            
            for table_name in report_tables:
                db.session.execute(text(f"DELETE FROM {table_name}"))
            
            # Re-enable foreign key checks
            db.session.execute(text("PRAGMA foreign_keys=ON"))
            
            db.session.commit()


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
        from core.managers.db_manager import db
        from core.model.product_type import ProductType
        from core.model.worker import PRESENTER_TYPES

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
        from core.managers.db_manager import db
        from core.model.product_type import ProductType
        from core.model.worker import PRESENTER_TYPES

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
        from core.managers.db_manager import db
        from core.model.report_item_type import ReportItemType
        from core.model.worker import PRESENTER_TYPES
        from core.model.product_type import ProductType

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

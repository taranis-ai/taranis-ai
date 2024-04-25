import pytest


@pytest.fixture(scope="session")
def cleanup_sources(app, request):
    with app.app_context():
        from core.model.osint_source import OSINTSource

        source_data = {
            "id": "42",
            "description": "This is a test source",
            "name": "Test Source",
            "parameters": [
                {"FEED_URL": "https://url/feed.xml"},
            ],
            "type": "rss_collector",
        }

        def teardown():
            with app.app_context():
                [OSINTSource.delete(source.id) for source in OSINTSource.get_all()]

        request.addfinalizer(teardown)

        yield source_data


@pytest.fixture(scope="session")
def cleanup_source_groups(app, request):
    with app.app_context():
        from core.model.osint_source import OSINTSourceGroup

        source_group_data = {
            "id": "42",
            "name": "Test Group",
            "description": "This is a test group",
        }

        def teardown():
            with app.app_context():
                if OSINTSourceGroup.get("42"):
                    print("Deleting test source group 42")
                    OSINTSourceGroup.delete("42")

        request.addfinalizer(teardown)

        yield source_group_data


@pytest.fixture(scope="session")
def cleanup_word_lists(app, request):
    with app.app_context():
        from core.model.word_list import WordList

        word_list_data = {
            "id": 42,
            "name": "Test word list name",
            "description": "Desc of word lists",
            "usage": ["TAGGING_BOT"],
            "link": "this.is.a.test.url.rocks",
            "entries": [],
        }

        def teardown():
            with app.app_context():
                if WordList.get(42):
                    print("Deleting test word list 42")
                    WordList.delete(42)

        request.addfinalizer(teardown)

        yield word_list_data


@pytest.fixture(scope="session")
def cleanup_user(app, request):
    with app.app_context():
        from core.model.user import User

        user_data = {
            "id": 42,
            "username": "testuser",
            "name": "Test User",
            "organization": 1,
            "roles": [2],
            "permissions": ["ANALYZE_ACCESS", "ANALYZE_CREATE", "ANALYZE_DELETE"],
            "password": "testpassword",
        }

        def teardown():
            with app.app_context():
                if User.get(42):
                    print("Deleting test user 42")
                    User.delete(42)

        request.addfinalizer(teardown)

        yield user_data


@pytest.fixture(scope="session")
def cleanup_role(app, request):
    with app.app_context():
        from core.model.role import Role

        role_data = {
            "id": 42,
            "name": "testrole",
            "description": "Test Role",
            "permissions": ["ANALYZE_ACCESS", "ANALYZE_CREATE", "ANALYZE_DELETE"],
        }

        def teardown():
            with app.app_context():
                if Role.get(42):
                    print("Deleting test user 42")
                    Role.delete(42)

        request.addfinalizer(teardown)

        yield role_data


@pytest.fixture(scope="session")
def cleanup_organization(app, request):
    with app.app_context():
        from core.model.organization import Organization

        organization_data = {
            "id": 42,
            "name": "testOrg",
            "description": "Test Organization",
            "address": {"street": "testStreet", "city": "testCity"},
        }

        def teardown():
            with app.app_context():
                if Organization.get(42):
                    print("Deleting test org 42")
                    Organization.delete(42)

        request.addfinalizer(teardown)

        yield organization_data


@pytest.fixture(scope="session")
def cleanup_bot(app, request):
    with app.app_context():
        from core.model.bot import Bot

        bot_data = {
            "id": "42",
            "name": "testBot",
            "description": "test Bot",
            "type": "nlp_bot",
            "parameters": {"SOURCE_GROUP": "default", "RUN_AFTER_COLLECTOR": "true"},
        }

        def teardown():
            with app.app_context():
                if Bot.get("42"):
                    print("Deleting test bot 42")
                    Bot.delete("42")

        request.addfinalizer(teardown)

        yield bot_data


@pytest.fixture(scope="session")
def cleanup_report_item_type(app, request):
    with app.app_context():
        from core.model.report_item_type import ReportItemType

        report_type_data = {
            "id": 42,
            "title": "Test Report Type",
            "description": "This is a test report type",
            "attribute_groups": [
                {
                    "index": 0,
                    "title": "Test Attribute Group",
                    "description": "This is a test attribute group",
                    "attribute_group_items": [
                        {
                            "index": 0,
                            "attribute_id": 1,
                            "title": "Test Attribute Group Item",
                            "description": "This is a test attribute group item",
                            "multiple": False,
                        }
                    ],
                }
            ],
        }

        def teardown():
            with app.app_context():
                if ReportItemType.get(42):
                    print("Deleting Report Type 42")
                    ReportItemType.delete(42)

        request.addfinalizer(teardown)

        yield report_type_data


@pytest.fixture(scope="session")
def cleanup_product_types(app, request):
    with app.app_context():
        from core.model.product_type import ProductType

        product_type_data = {
            "id": 42,
            "type": "pdf_presenter",
            "parameters": {"TEMPLATE_PATH": "template path"},
            "title": "Test Product type",
            "description": "Product type desc",
        }

        def teardown():
            with app.app_context():
                if ProductType.get(42):
                    print("Deleting test product type 42")
                    ProductType.delete(42)

        request.addfinalizer(teardown)

        yield product_type_data


@pytest.fixture(scope="session")
def cleanup_acls(app, request):
    with app.app_context():
        from core.model.role_based_access import RoleBasedAccess

        acl_data = {
            "id": 42,
            "name": "test_acl_unique",
            "description": "Test ACL",
            "item_type": "word_list",
            "item_id": "acl_id",
            "roles": [],
        }

        def teardown():
            with app.app_context():
                if RoleBasedAccess.get(42):
                    print("Deleting test ACL 42")
                    RoleBasedAccess.delete(42)

        request.addfinalizer(teardown)

        yield acl_data


@pytest.fixture(scope="session")
def cleanup_publisher_preset(app, request):
    with app.app_context():
        from core.model.publisher_preset import PublisherPreset

        publisher_preset_data = {
            "id": "44",
            "name": "test_publisher_preset",
            "description": "Test ACL",
            "type": "ftp_publisher",
            "parameters": {"FTP_URL": "ftp_url_entry"},
        }

        def teardown():
            with app.app_context():
                if PublisherPreset.get(44):
                    print("Deleting test publisher preset 44")
                    PublisherPreset.delete(44)

        request.addfinalizer(teardown)

        yield publisher_preset_data


@pytest.fixture(scope="session")
def cleanup_attribute(app, request):
    with app.app_context():
        from core.model.attribute import Attribute

        attribute_data = {
            "id": 42,
            "name": "Attribute name",
            "description": "Simple attribute desc",
            "type": "STRING",
            "default_value": "2234",
        }

        def teardown():
            with app.app_context():
                if Attribute.get(42):
                    print("Deleting test attribute 42")
                    Attribute.delete(42)

        request.addfinalizer(teardown)

        yield attribute_data


@pytest.fixture(scope="session")
def cleanup_worker_types(app, request):
    with app.app_context():
        from core.model.worker import Worker

        worker_types_data = {
            "name": "Worker type",
            "description": "Desc of worker type",
            "type": "web_collector",
            "parameters": {
                "REGULAR_EXPRESSION": "Reg Exp",
                "ITEM_FILTER": "Item Filter",
                "RUN_AFTER_COLLECTOR": "Run After Collector",
                "REFRESH_INTERVAL": "Refresh Interval",
            },
        }

        # Because id is not assignable, the teardown is not possible. Any thoughts?
        def teardown():
            with app.app_context():
                if Worker.get(42):
                    print("Deleting test attribute 42")
                    Worker.delete(42)

        request.addfinalizer(teardown)

        yield worker_types_data

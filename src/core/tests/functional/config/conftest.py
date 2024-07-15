import pytest


@pytest.fixture(scope="session")
def cleanup_sources(app):
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

        yield source_data

        if OSINTSource.get(source_data["id"]):
            OSINTSource.delete(source_data["id"])


@pytest.fixture(scope="session")
def cleanup_source_groups(app):
    with app.app_context():
        from core.model.osint_source import OSINTSourceGroup

        source_group_data = {
            "id": "42",
            "name": "Test Group",
            "description": "This is a test group",
        }

        yield source_group_data

        if OSINTSourceGroup.get(source_group_data["id"]):
            OSINTSourceGroup.delete(source_group_data["id"])


@pytest.fixture(scope="session")
def cleanup_word_lists(app):
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

        yield word_list_data

        if WordList.get(word_list_data["id"]):
            WordList.delete(word_list_data["id"])


@pytest.fixture(scope="session")
def cleanup_user(app):
    with app.app_context():
        from core.model.user import User

        user_data = {
            "id": 42,
            "username": "testuser",
            "name": "Test User",
            "organization": 1,
            "roles": [2],
            "password": "testpassword",
        }

        yield user_data

        if User.get(user_data["id"]):
            User.delete(user_data["id"])


@pytest.fixture(scope="session")
def cleanup_role(app):
    with app.app_context():
        from core.model.role import Role

        role_data = {
            "id": 42,
            "name": "testrole",
            "description": "Test Role",
            "permissions": ["ANALYZE_ACCESS", "ANALYZE_CREATE", "ANALYZE_DELETE"],
        }

        yield role_data

        if Role.get(role_data["id"]):
            Role.delete(role_data["id"])


@pytest.fixture(scope="session")
def cleanup_organization(app):
    with app.app_context():
        from core.model.organization import Organization

        organization_data = {
            "id": 42,
            "name": "testOrg",
            "description": "Test Organization",
            "address": {"street": "testStreet", "city": "testCity"},
        }

        yield organization_data

        if Organization.get(organization_data["id"]):
            Organization.delete(organization_data["id"])


@pytest.fixture(scope="session")
def cleanup_bot(app):
    with app.app_context():
        from core.model.bot import Bot

        bot_data = {
            "id": "42",
            "name": "testBot",
            "description": "test Bot",
            "type": "nlp_bot",
            "parameters": {"SOURCE_GROUP": "default", "RUN_AFTER_COLLECTOR": "true"},
        }

        yield bot_data

        if Bot.get(bot_data["id"]):
            Bot.delete(bot_data["id"])


@pytest.fixture(scope="session")
def cleanup_report_item_type(app):
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
                            "required": False,
                        }
                    ],
                }
            ],
        }

        yield report_type_data

        if ReportItemType.get(report_type_data["id"]):
            ReportItemType.delete(report_type_data["id"])


@pytest.fixture(scope="session")
def cleanup_product_types(app):
    with app.app_context():
        from core.model.product_type import ProductType

        product_type_data = {
            "id": 42,
            "type": "pdf_presenter",
            "parameters": {"TEMPLATE_PATH": "template path"},
            "title": "Test Product type",
            "description": "Product type desc",
        }

        yield product_type_data

        if ProductType.get(product_type_data["id"]):
            ProductType.delete(product_type_data["id"])


@pytest.fixture(scope="session")
def cleanup_acls(app):
    with app.app_context():
        from core.model.role_based_access import RoleBasedAccess

        rbac_data = {
            "id": 42,
            "name": "test_acl_unique",
            "description": "Test ACL",
            "item_type": "word_list",
            "item_id": "acl_id",
            "roles": [],
        }

        yield rbac_data

        if RoleBasedAccess.get(rbac_data["id"]):
            RoleBasedAccess.delete(rbac_data["id"])


@pytest.fixture(scope="session")
def cleanup_publisher_preset(app):
    with app.app_context():
        from core.model.publisher_preset import PublisherPreset

        publisher_presets = {
            "id": "42",
            "name": "test_publisher_preset",
            "description": "Test ACL",
            "type": "ftp_publisher",
            "parameters": {"FTP_URL": "ftp_url_entry"},
        }

        yield publisher_presets

        if PublisherPreset.get(publisher_presets["id"]):
            PublisherPreset.delete(publisher_presets["id"])


@pytest.fixture(scope="session")
def cleanup_attribute(app):
    with app.app_context():
        from core.model.attribute import Attribute

        attribute_data = {
            "id": 42,
            "name": "Attribute name",
            "description": "Simple attribute desc",
            "type": "STRING",
            "default_value": "2234",
        }

        yield attribute_data

        if Attribute.get(attribute_data["id"]):
            Attribute.delete(attribute_data["id"])


@pytest.fixture(scope="session")
def cleanup_worker_types(app):
    with app.app_context():
        from core.model.worker import Worker

        if rss_worker := Worker.filter_by_type("rss_collector"):
            yield rss_worker.to_dict()

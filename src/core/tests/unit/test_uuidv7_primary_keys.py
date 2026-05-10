import uuid

from core.model.base_model import BaseModel
from core.model.osint_source import OSINTSource, OSINTSourceGroup
from core.model.permission import Permission
from core.model.product_type import ProductType
from core.model.role import Role
from core.model.settings import Settings
from core.model.story import Story
from core.model.user import User


def assert_uuid7(value: str):
    parsed = uuid.UUID(value)
    assert str(parsed) == value
    assert parsed.version == 7


def test_uuid7_helper_generates_canonical_uuidv7():
    assert_uuid7(BaseModel.uuid7_str())


def test_explicit_canonical_uuid_is_preserved():
    explicit_id = str(uuid.uuid7())
    story = Story(id=explicit_id, title="Explicit ID")
    assert story.id == explicit_id


def test_seeded_semantic_records_use_uuid_ids(app):
    with app.app_context():
        manual_source = OSINTSource.get_by_key("manual")
        default_group = OSINTSourceGroup.get_by_key("default")
        permission = Permission.get_by_code("ASSESS_ACCESS")
        settings = Settings.get_settings_entry()

        assert manual_source is not None
        assert manual_source.key == "manual"
        assert_uuid7(manual_source.id)

        assert default_group is not None
        assert default_group.key == "default"
        assert_uuid7(default_group.id)

        assert permission is not None
        assert permission.code == "ASSESS_ACCESS"
        assert_uuid7(permission.id)

        assert settings is not None
        assert settings.singleton_key == "settings"
        assert_uuid7(settings.id)


def test_representative_converted_seeded_models_use_uuid_ids(app):
    with app.app_context():
        admin = User.find_by_name("admin")
        role = Role.filter_by_name("Admin")
        product_type = ProductType.filter_by_title("Default PDF Presenter")

        assert admin is not None
        assert role is not None
        assert product_type is not None
        assert_uuid7(admin.id)
        assert_uuid7(role.id)
        assert_uuid7(product_type.id)
        assert admin.roles[0].id == role.id

import uuid

from core.model.asset import AssetGroup
from core.model.base_model import BaseModel
from core.model.osint_source import OSINTSource, OSINTSourceGroup
from core.model.permission import Permission
from core.model.product_type import ProductType
from core.model.role import Role
from core.model.settings import Settings
from core.model.story import Story
from core.model.task import Task
from core.model.user import User


def assert_uuid7(value: str):
    parsed = uuid.UUID(value)
    assert str(parsed) == value
    assert parsed.version == 7


def assert_string_id(value: str):
    assert isinstance(value, str)
    assert value


def test_uuid7_helper_generates_canonical_uuidv7():
    assert_uuid7(BaseModel.uuid7_str())


def test_new_model_defaults_generate_uuidv7():
    story = Story(title="Generated ID")
    task = Task(id="legacy-job-reference")

    assert_uuid7(story.id)
    assert_uuid7(task.id)
    assert task.job_id == "legacy-job-reference"


def test_explicit_canonical_uuid_is_preserved():
    explicit_id = str(uuid.uuid7())
    story = Story(id=explicit_id, title="Explicit ID")
    assert story.id == explicit_id


def test_seeded_semantic_records_keep_string_ids_and_lookup_aliases(app):
    with app.app_context():
        manual_source = OSINTSource.get_by_key("manual")
        default_group = OSINTSourceGroup.get_by_key("default")
        default_asset_group = AssetGroup.get_by_key("default")
        permission = Permission.get_by_code("ASSESS_ACCESS")
        settings = Settings.get_settings_entry()

        assert manual_source is not None
        assert manual_source.key == "manual"
        assert_string_id(manual_source.id)
        assert OSINTSource.get(manual_source.id) == manual_source
        assert OSINTSource.get("manual") == manual_source

        assert default_group is not None
        assert default_group.key == "default"
        assert_string_id(default_group.id)
        assert OSINTSourceGroup.get(default_group.id) == default_group
        assert OSINTSourceGroup.get("default") == default_group

        assert default_asset_group is not None
        assert default_asset_group.key == "default"
        assert_string_id(default_asset_group.id)
        assert AssetGroup.get(default_asset_group.id) == default_asset_group
        assert AssetGroup.get("default") == default_asset_group

        assert permission is not None
        assert permission.code == "ASSESS_ACCESS"
        assert_string_id(permission.id)
        assert Permission.get(permission.id) == permission
        assert Permission.get("ASSESS_ACCESS") == permission

        assert settings is not None
        assert settings.singleton_key == "settings"
        assert_string_id(settings.id)
        assert Settings.get(1) == settings
        assert Settings.get("settings") == settings


def test_representative_converted_seeded_models_use_string_ids(app):
    with app.app_context():
        admin = User.find_by_name("admin")
        role = Role.filter_by_name("Admin")
        product_type = ProductType.filter_by_title("Default PDF Presenter")

        assert admin is not None
        assert role is not None
        assert product_type is not None
        assert_string_id(admin.id)
        assert_string_id(role.id)
        assert_string_id(product_type.id)
        assert admin.roles[0].id == role.id


def test_task_lookup_supports_preserved_legacy_job_id(app, session):
    with app.app_context():
        task = Task(id="legacy-job-for-uuid-test")
        session.add(task)
        session.flush()

        assert_uuid7(task.id)
        assert Task.get("legacy-job-for-uuid-test") == task
        assert Task.get_by_job_id("legacy-job-for-uuid-test") == task

from copy import deepcopy

from core.model.settings import Settings
from core.model.user import User


def test_missing_global_onboarding_defaults_to_enabled(session, admin_user):
    settings = Settings.get_settings_entry()
    assert settings is not None
    settings.settings = {key: value for key, value in settings.settings.items() if key != "onboarding_enabled"}
    session.flush()

    Settings.initialize()

    assert settings.settings["onboarding_enabled"] is True
    assert admin_user.profile["onboarding_enabled"] is True


def test_global_and_per_user_onboarding_controls(session, admin_user):
    settings = Settings.get_settings_entry()
    assert settings is not None
    settings.settings = {**Settings.with_defaults(settings.settings), "onboarding_enabled": True}
    onboarding_tasks = deepcopy(admin_user.profile.get("onboarding_tasks", {}))
    session.flush()

    response, status = Settings.update({"settings": {"onboarding_enabled": "false"}})

    assert status == 200
    assert response["settings"]["onboarding_enabled"] is False
    assert admin_user.profile["onboarding_enabled"] is False
    assert admin_user.profile["onboarding_tasks"] == onboarding_tasks

    User.update(admin_user.id, {"profile": {"onboarding_enabled": True}})

    Settings.update({"settings": {"onboarding_enabled": False}})

    assert admin_user.profile["onboarding_enabled"] is True
    assert admin_user.to_user_profile().pending_onboarding_tasks

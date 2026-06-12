from models.user import ProfileSettings

from core.model.user import User


def test_user_timezone_override_wins_over_global_default(monkeypatch):
    monkeypatch.setattr("core.model.user.Settings.get_settings", lambda: {"default_timezone": "UTC"})

    assert User.resolve_effective_timezone(ProfileSettings(timezone="Europe/Vienna")) == "Europe/Vienna"


def test_user_effective_timezone_uses_global_default(monkeypatch):
    monkeypatch.setattr("core.model.user.Settings.get_settings", lambda: {"default_timezone": "Europe/Vienna"})

    assert User.resolve_effective_timezone(ProfileSettings(timezone=None)) == "Europe/Vienna"


def test_user_effective_timezone_falls_back_to_utc(monkeypatch):
    monkeypatch.setattr("core.model.user.Settings.get_settings", lambda: {})

    assert User.resolve_effective_timezone(ProfileSettings(timezone=None)) == "UTC"


def test_update_profile_sets_timezone_override(session, admin_user):
    response, status = User.update_profile(admin_user, {"timezone": "Europe/Vienna"})

    assert status == 200
    assert response["user_profile"]["timezone"] == "Europe/Vienna"
    assert admin_user.profile["timezone"] == "Europe/Vienna"


def test_update_profile_clears_timezone_override(session, admin_user):
    admin_user.profile = {**(admin_user.profile or {}), "timezone": "Europe/Vienna"}
    session.flush()

    response, status = User.update_profile(admin_user, {"timezone": ""})

    assert status == 200
    assert "timezone" not in response["user_profile"]
    assert "timezone" not in admin_user.profile


def test_update_profile_rejects_invalid_timezone(session, admin_user):
    response, status = User.update_profile(admin_user, {"timezone": "Not/A_Timezone"})

    assert status == 400
    assert "Invalid timezone" in response["error"]

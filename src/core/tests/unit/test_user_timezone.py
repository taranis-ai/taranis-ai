from core.model.user import User


def test_new_user_copies_global_timezone_once(session, admin_user, monkeypatch):
    monkeypatch.setattr("core.model.user.Settings.get_settings", lambda: {"default_timezone": "Europe/Vienna"})
    user = User(
        username="timezone-test",
        name="Timezone Test",
        organization=admin_user.organization.id,
        roles=[role.id for role in admin_user.roles],
    )

    monkeypatch.setattr("core.model.user.Settings.get_settings", lambda: {"default_timezone": "America/New_York"})

    assert user.profile["timezone"] == "Europe/Vienna"
    assert user.to_user_profile().effective_timezone == "Europe/Vienna"


def test_update_profile_sets_timezone_override(session, admin_user):
    response, status = User.update_profile(admin_user, {"timezone": "Europe/Vienna"})

    assert status == 200
    assert response["user_profile"]["timezone"] == "Europe/Vienna"
    assert admin_user.profile["timezone"] == "Europe/Vienna"
    assert admin_user.to_user_profile().effective_timezone == "Europe/Vienna"


def test_update_profile_clears_timezone_override(session, admin_user, monkeypatch):
    monkeypatch.setattr("core.model.user.Settings.get_settings", lambda: {"default_timezone": "Europe/Vienna"})
    admin_user.profile = {**(admin_user.profile or {}), "timezone": "Europe/Vienna"}
    session.flush()

    response, status = User.update_profile(admin_user, {"timezone": ""})

    assert status == 200
    assert "timezone" not in response["user_profile"]
    assert "timezone" not in admin_user.profile
    assert admin_user.to_user_profile().effective_timezone == "UTC"


def test_update_profile_rejects_invalid_timezone(session, admin_user):
    response, status = User.update_profile(admin_user, {"timezone": "Not/A_Timezone"})

    assert status == 400
    assert "Invalid timezone" in response["error"]

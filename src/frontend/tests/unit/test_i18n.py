from datetime import datetime

import pytest
from flask_babel import get_locale
from flask_jwt_extended import create_access_token
from models.user import ProfileSettings, UserProfile

from frontend.auth import render_login_page
from frontend.cache import add_user_to_cache
from frontend.filters import format_datetime


LOCAL_TIME = datetime(2026, 6, 11, 10, 30)


def _user_with_language(language: str, timezone: str | None = None) -> UserProfile:
    return UserProfile(
        id=f"user-{language}",
        username=f"user-{language}",
        name="Test User",
        organization={"id": "1", "name": "Test Organization"},
        permissions=["ASSESS_ACCESS"],
        profile=ProfileSettings(language=language, timezone=timezone),
        roles=[{"id": "1", "name": "User"}],
    )


def _access_token_for_user(app, user: UserProfile) -> str:
    add_user_to_cache(user.model_dump(mode="json"))
    with app.app_context():
        return create_access_token(identity=user)


def _authenticated_client_for_user(app, user: UserProfile):
    client = app.test_client()
    client.set_cookie(key="access_token_cookie", value=_access_token_for_user(app, user))
    return client


def _request_context(app, headers: dict[str, str] | None = None, user: UserProfile | None = None):
    request_headers = dict(headers or {})
    if user:
        request_headers["Cookie"] = f"access_token_cookie={_access_token_for_user(app, user)}"
    return app.test_request_context("/frontend/login", headers=request_headers)


@pytest.mark.parametrize(
    ("language", "headers", "expected_text"),
    [
        ("de", {}, "Benutzereinstellungen"),
        ("es", {"Accept-Language": "de"}, "Passwort ändern"),
    ],
)
def test_settings_page_selects_profile_or_accepted_language(app, test_cache_backend, language, headers, expected_text):
    client = _authenticated_client_for_user(app, _user_with_language(language))

    response = client.get(f"{app.config['APPLICATION_ROOT']}settings", headers=headers)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'lang="de"' in html
    assert expected_text in html


@pytest.mark.parametrize(
    ("headers", "expected_language", "expected_text"),
    [
        ({"Accept-Language": "de"}, "de", "Benutzername"),
        ({"Accept-Language": "de-AT,en-US;q=0.9,en;q=0.8"}, "de", "Benutzername"),
        ({}, "en", "Username"),
    ],
)
def test_login_page_selects_locale(app, headers, expected_language, expected_text):
    with _request_context(app, headers):
        html = render_login_page()

    assert str(get_locale()) == expected_language
    assert f'lang="{expected_language}"' in html
    assert expected_text in html


def test_authenticated_timezone_formats_naive_utc_datetime_as_local_time(app, test_cache_backend):
    user = _user_with_language("de", timezone="Europe/Vienna")

    with _request_context(app, {"Accept-Language": "de"}, user):
        assert format_datetime(LOCAL_TIME) == "11. Juni 2026 12:30"


def test_timezone_cookie_does_not_affect_datetime_formatting(app):
    with _request_context(app, {"Accept-Language": "de", "Cookie": "taranis_timezone=Europe/Vienna"}):
        assert format_datetime(LOCAL_TIME) == "11. Juni 2026 10:30"

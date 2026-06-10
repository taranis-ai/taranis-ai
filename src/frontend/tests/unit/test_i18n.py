from flask_babel import get_locale
from flask_jwt_extended import create_access_token
from models.user import ProfileSettings, UserProfile

from frontend.auth import render_login_page
from frontend.cache import add_user_to_cache


def _user_with_language(language: str) -> UserProfile:
    return UserProfile(
        id=f"user-{language}",
        username=f"user-{language}",
        name="Test User",
        organization={"id": "1", "name": "Test Organization"},
        permissions=["ASSESS_ACCESS"],
        profile=ProfileSettings(language=language),
        roles=[{"id": "1", "name": "User"}],
    )


def _authenticated_client_for_user(app, user: UserProfile):
    add_user_to_cache(user.model_dump(mode="json"))
    with app.app_context():
        access_token = create_access_token(identity=user)
    client = app.test_client()
    client.set_cookie(key="access_token_cookie", value=access_token)
    return client


def test_authenticated_user_profile_language_selects_german(app, test_cache_backend):
    client = _authenticated_client_for_user(app, _user_with_language("de"))

    response = client.get(f"{app.config['APPLICATION_ROOT']}settings")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'lang="de"' in html
    assert 'data-confirm-cancel="Abbrechen"' in html
    assert "Änderungen speichern" in html
    assert "Benutzereinstellungen" in html


def test_unsupported_profile_language_falls_back_to_accept_language(app, test_cache_backend):
    client = _authenticated_client_for_user(app, _user_with_language("es"))

    response = client.get(f"{app.config['APPLICATION_ROOT']}settings", headers={"Accept-Language": "de"})

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'lang="de"' in html
    assert "Passwort ändern" in html


def test_anonymous_login_page_uses_accept_language(app):
    with app.test_request_context("/frontend/login", headers={"Accept-Language": "de"}):
        html = render_login_page()

    assert 'lang="de"' in html
    assert 'data-confirm-cancel="Abbrechen"' in html
    assert "Benutzername" in html
    assert "Anmelden" in html


def test_anonymous_login_page_uses_regional_accept_language(app):
    with app.test_request_context("/frontend/login", headers={"Accept-Language": "de-AT,en-US;q=0.9,en;q=0.8"}):
        html = render_login_page()

    assert 'lang="de"' in html
    assert "Benutzername" in html
    assert "Anmelden" in html


def test_english_is_default_locale(app):
    with app.test_request_context("/frontend/login"):
        html = render_login_page()

    assert str(get_locale()) == "en"
    assert 'lang="en"' in html
    assert "Username" in html

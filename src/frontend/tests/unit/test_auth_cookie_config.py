from http.cookies import SimpleCookie

import pytest
from flask import Flask, render_template, url_for
from flask_jwt_extended import create_access_token, set_access_cookies
from pydantic import ValidationError

from frontend import create_app
from frontend.config import Settings


@pytest.mark.parametrize(
    ("base_path", "suffix", "expected_names"),
    [
        ("/", "", ("access_token_cookie", "csrf_access_token")),
        ("/q/", "_q", ("access_token_cookie_q", "csrf_access_token_q")),
    ],
)
def test_jwt_cookie_names_and_paths(base_path: str, suffix: str, expected_names: tuple[str, ...]) -> None:
    settings = Settings(TARANIS_BASE_PATH=base_path, JWT_COOKIE_SUFFIX=suffix)
    flask_app = Flask(__name__)
    flask_app.config.from_object(settings)
    names = (
        settings.JWT_ACCESS_COOKIE_NAME,
        settings.JWT_ACCESS_CSRF_COOKIE_NAME,
    )
    paths = (
        settings.JWT_ACCESS_COOKIE_PATH,
        settings.JWT_ACCESS_CSRF_COOKIE_PATH,
    )

    assert names == expected_names
    assert paths == (base_path,) * 2
    assert (
        tuple(
            flask_app.config[name]
            for name in (
                "JWT_ACCESS_COOKIE_NAME",
                "JWT_ACCESS_CSRF_COOKIE_NAME",
            )
        )
        == expected_names
    )
    assert all(
        flask_app.config[name] == base_path
        for name in (
            "JWT_ACCESS_COOKIE_PATH",
            "JWT_ACCESS_CSRF_COOKIE_PATH",
        )
    )


def test_jwt_cookie_suffix_rejects_invalid_characters() -> None:
    with pytest.raises(ValidationError, match="JWT_COOKIE_SUFFIX"):
        Settings(JWT_COOKIE_SUFFIX="/q")


def test_otlp_endpoint_is_normalized() -> None:
    settings = Settings(OTEL_EXPORTER_OTLP_ENDPOINT="  http://telemetry:4318/  ")

    assert settings.OTEL_EXPORTER_OTLP_ENDPOINT == "http://telemetry:4318"


def test_form_reads_configured_csrf_cookie(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(app.config, "JWT_ACCESS_CSRF_COOKIE_NAME", "csrf_access_token_q")

    with app.test_request_context(headers={"Cookie": "csrf_access_token_q=csrf-value"}):
        body = render_template(
            "default/admin_form.html",
            submit_text="Save",
            model_name="example",
            form_action="/example",
        )

    assert 'name="csrf_token" value="csrf-value"' in body


@pytest.mark.parametrize("debug", [False, True])
def test_production_cookie_and_header_defaults(debug, auth_user):
    app = create_app({"TESTING": True, "DEBUG": debug})
    with app.test_request_context():
        response = app.response_class()
        set_access_cookies(response, create_access_token(identity=auth_user))
        cookies = SimpleCookie()
        for header in response.headers.getlist("Set-Cookie"):
            cookies.load(header)
        assert bool(cookies[app.config["JWT_ACCESS_COOKIE_NAME"]]["secure"]) is not debug
        assert cookies[app.config["JWT_ACCESS_COOKIE_NAME"]]["httponly"]
        assert cookies[app.config["JWT_ACCESS_COOKIE_NAME"]]["samesite"] == "Lax"
        assert app.config["SESSION_COOKIE_SECURE"] is not debug

    client = app.test_client()
    response = client.get("/missing")
    assert response.status_code == 404
    if debug:
        assert "Content-Security-Policy" not in response.headers
        assert "Strict-Transport-Security" not in response.headers
    else:
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["Strict-Transport-Security"] == "max-age=31536000"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "microphone=()" in response.headers["Permissions-Policy"]
        assert "object-src 'none'" in response.headers["Content-Security-Policy"]
        assert "frame-ancestors 'self'" in response.headers["Content-Security-Policy"]
    with app.test_request_context():
        static_path = url_for("static", filename="js/main.js")
        swagger_path = url_for("api_doc.static", filename="swagger-ui-bundle.js")
    for path in (static_path, swagger_path):
        static = client.get(path)
        assert static.status_code == 200
        assert "no-store" not in static.headers.get("Cache-Control", "")

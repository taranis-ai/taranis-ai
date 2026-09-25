from http.cookies import SimpleCookie

import pytest
from flask import Flask, jsonify, session
from flask_jwt_extended import JWTManager, create_access_token, set_access_cookies

from core.security import init_app


@pytest.mark.parametrize("debug", [False, True])
def test_security_defaults_on_cookies_responses_and_static_files(debug, tmp_path):
    (tmp_path / "test.css").write_text("body {}")
    app = Flask(__name__, static_folder=str(tmp_path), static_url_path="/static")
    app.config.update(DEBUG=debug, SECRET_KEY="test-only-session-key", JWT_SECRET_KEY="test-only-jwt-key-with-32-characters")
    init_app(app)
    JWTManager(app)

    @app.get("/private")
    def private():
        session["test"] = True
        response = jsonify(ok=True)
        response.headers["Cache-Control"] = "private, max-age=300"
        set_access_cookies(response, create_access_token(identity="test"))
        return response

    @app.get("/report")
    def report():
        return "report", {"Content-Security-Policy": "sandbox allow-scripts allow-downloads"}

    client = app.test_client()
    response = client.get("/private", base_url="https://localhost")
    cookies = SimpleCookie()
    for header in response.headers.getlist("Set-Cookie"):
        cookies.load(header)
    for name in ("access_token_cookie", "csrf_access_token", "session"):
        assert bool(cookies[name]["secure"]) is not debug
        assert cookies[name]["samesite"] == "Lax"
    assert cookies["access_token_cookie"]["httponly"]
    assert cookies["session"]["httponly"]
    assert not cookies["csrf_access_token"]["httponly"]
    assert response.headers["Cache-Control"] == ("private, max-age=300" if debug else "no-store")
    error = client.get("/missing")
    assert error.status_code == 404
    for result in (response, error):
        if debug:
            assert "Strict-Transport-Security" not in result.headers
            assert "Content-Security-Policy" not in result.headers
        else:
            assert result.headers["Strict-Transport-Security"] == "max-age=31536000"
            assert result.headers["X-Content-Type-Options"] == "nosniff"
            assert result.headers["X-Frame-Options"] == "SAMEORIGIN"
            assert result.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
            assert "camera=()" in result.headers["Permissions-Policy"]
            assert "default-src 'none'" in result.headers["Content-Security-Policy"]
    static = client.get("/static/test.css")
    assert static.status_code == 200
    assert "no-store" not in static.headers["Cache-Control"]
    assert client.get("/report").headers["Content-Security-Policy"] == "sandbox allow-scripts allow-downloads"

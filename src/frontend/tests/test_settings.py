def test_flask_secret_key(app):
    with app.app_context():
        secret_key = app.config.get("JWT_ACCESS_COOKIE_NAME", None)
        assert secret_key == "access_token_cookie"

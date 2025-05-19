def test_api_key(app):
    from core.config import Config

    with app.app_context():
        api_key = Config.API_KEY.get_secret_value()
        assert api_key == "test_key"


def test_flask_secret_key(app):
    with app.app_context():
        secret_key = app.config.get("JWT_SECRET_KEY", None)
        assert secret_key == "test_key"

def test_api_key():
    from core.config import Config

    api_key = Config.API_KEY
    assert api_key == "test_key"


def test_flask_secret_key(app):
    secret_key = app.config.get("SECRET_KEY", None)
    assert secret_key == "test_key"

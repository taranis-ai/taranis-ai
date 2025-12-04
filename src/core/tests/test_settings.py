from pydantic import SecretStr
from core.config import Settings

def test_psycopg_multi_host_uri(monkeypatch):
    """
    Tests that the Settings class correctly parses and masks a multi-host PostgreSQL connection URI.
    Also verifies engine options and connect timeout configuration.
    """
    raw_uri = (
        "postgresql+psycopg://user:pass@db-1:5432,db-2:5432,db-3:5432/"
        "taranis?target_session_attrs=primary"
    )

    # raw_uri = (
    #     "postgresql+psycopg://app:apppass@/appdb?host=127.0.0.1,127.0.0.1&port=54321,54322&target_session_attrs=read-write&connect_timeout=3"
    # )
    monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
    settings = Settings(SQLALCHEMY_DATABASE_URI=raw_uri, DB_PASSWORD=SecretStr("pass"))

    assert settings.SQLALCHEMY_DATABASE_URI == raw_uri
    # Masked value should exist but we avoid pinning to the placeholder string.
    assert settings.SQLALCHEMY_DATABASE_URI_MASK
    assert settings.SQLALCHEMY_DATABASE_URI_MASK != settings.SQLALCHEMY_DATABASE_URI
    assert settings.SQLALCHEMY_ENGINE_OPTIONS["connect_args"] == {
        "connect_timeout": settings.SQLALCHEMY_CONNECT_TIMEOUT
    }

def test_api_key(app):
    from core.config import Config

    with app.app_context():
        api_key = Config.API_KEY.get_secret_value()
        assert api_key == "test_key"


def test_flask_secret_key(app):
    with app.app_context():
        secret_key = app.config.get("JWT_SECRET_KEY", None)
        assert secret_key == "test_key"

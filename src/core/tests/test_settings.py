from pydantic import SecretStr
import pytest
from core.config import Settings

@pytest.mark.parametrize(
    "raw_uri",
    [
        # Host/port in authority section, multiple hosts
        "postgresql+psycopg://user:pass@db-1:5432,db-2:5432,db-3:5432/appdb?target_session_attrs=primary&connect_timeout=3",
        # Host/port in query string, multiple hosts
        "postgresql+psycopg://user:pass@/appdb?host=db-1,db-2,db-3&port=5432,5432,5432&target_session_attrs=primary&connect_timeout=3",
    ],
)
def test_psycopg_multi_host_uri(monkeypatch, raw_uri):
    """
    Tests that the Settings class correctly parses and masks a multi-host PostgreSQL connection URI.
    Also verifies engine options and connect timeout configuration.
    """
    monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
    settings = Settings(SQLALCHEMY_DATABASE_URI=raw_uri, DB_PASSWORD=SecretStr("pass"))

    assert settings.SQLALCHEMY_DATABASE_URI == raw_uri
    assert settings.SQLALCHEMY_DATABASE_URI_MASK
    assert settings.SQLALCHEMY_DATABASE_URI_MASK != settings.SQLALCHEMY_DATABASE_URI
    assert settings.DB_PASSWORD.get_secret_value() not in settings.SQLALCHEMY_DATABASE_URI_MASK
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

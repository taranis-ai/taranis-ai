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
    assert "db-1" in settings.SQLALCHEMY_DATABASE_URI
    assert "db-2" in settings.SQLALCHEMY_DATABASE_URI
    assert "db-3" in settings.SQLALCHEMY_DATABASE_URI
    assert settings.SQLALCHEMY_ENGINE_OPTIONS["connect_args"] == {"connect_timeout": settings.SQLALCHEMY_CONNECT_TIMEOUT}


def test_api_key(app):
    from core.config import Config

    with app.app_context():
        api_key = Config.API_KEY.get_secret_value()
        assert api_key == "test_key"


def test_flask_secret_key(app):
    with app.app_context():
        secret_key = app.config.get("JWT_SECRET_KEY", None)
        assert secret_key == "test_key"


def test_sqlalchemy_pool_timeout_env_var(monkeypatch):
    """Test that SQLALCHEMY_POOL_TIMEOUT is correctly read from environment and added to engine options."""
    monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
    monkeypatch.delenv("SQLALCHEMY_POOL_TIMEOUT", raising=False)

    settings = Settings(SQLALCHEMY_POOL_TIMEOUT=666)

    assert settings.SQLALCHEMY_POOL_TIMEOUT == 666
    assert settings.SQLALCHEMY_ENGINE_OPTIONS["pool_timeout"] == 666


def test_sqlalchemy_pool_timeout_not_set(monkeypatch):
    """Test that SQLALCHEMY_POOL_TIMEOUT is optional and not added to engine options when None."""
    monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
    monkeypatch.delenv("SQLALCHEMY_POOL_TIMEOUT", raising=False)

    settings = Settings()

    assert settings.SQLALCHEMY_POOL_TIMEOUT is None
    assert "pool_timeout" not in settings.SQLALCHEMY_ENGINE_OPTIONS


def test_sqlalchemy_pool_recycle_env_var(monkeypatch):
    """Test that SQLALCHEMY_POOL_RECYCLE is correctly read from environment and added to engine options."""
    monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
    monkeypatch.delenv("SQLALCHEMY_POOL_RECYCLE", raising=False)

    settings = Settings(SQLALCHEMY_POOL_RECYCLE=3600)

    assert settings.SQLALCHEMY_POOL_RECYCLE == 3600
    assert settings.SQLALCHEMY_ENGINE_OPTIONS["pool_recycle"] == 3600


def test_sqlalchemy_pool_recycle_not_set(monkeypatch):
    """Test that SQLALCHEMY_POOL_RECYCLE is optional and not added to engine options when None."""
    monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
    monkeypatch.delenv("SQLALCHEMY_POOL_RECYCLE", raising=False)

    settings = Settings()

    assert settings.SQLALCHEMY_POOL_RECYCLE is None
    assert "pool_recycle" not in settings.SQLALCHEMY_ENGINE_OPTIONS


def test_sqlalchemy_pool_timeout_and_recycle_both_set(monkeypatch):
    """Test that both SQLALCHEMY_POOL_TIMEOUT and SQLALCHEMY_POOL_RECYCLE are added to engine options."""
    monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
    monkeypatch.delenv("SQLALCHEMY_POOL_TIMEOUT", raising=False)
    monkeypatch.delenv("SQLALCHEMY_POOL_RECYCLE", raising=False)

    settings = Settings(SQLALCHEMY_POOL_TIMEOUT=666, SQLALCHEMY_POOL_RECYCLE=3600)

    assert settings.SQLALCHEMY_POOL_TIMEOUT == 666
    assert settings.SQLALCHEMY_POOL_RECYCLE == 3600
    assert settings.SQLALCHEMY_ENGINE_OPTIONS["pool_timeout"] == 666
    assert settings.SQLALCHEMY_ENGINE_OPTIONS["pool_recycle"] == 3600


def test_sqlalchemy_engine_options_includes_pool_size_and_max_overflow(monkeypatch):
    """Test that basic pool size and max overflow are always included in engine options."""
    monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)

    settings = Settings()

    assert settings.SQLALCHEMY_ENGINE_OPTIONS["pool_size"] == settings.SQLALCHEMY_POOL_SIZE
    assert settings.SQLALCHEMY_ENGINE_OPTIONS["max_overflow"] == settings.SQLALCHEMY_MAX_OVERFLOW


def test_pool_options_applied_to_actual_engine(app):
    """Integration test: verify default pool options are applied to the actual Flask app's database engine."""
    from core.managers.db_manager import db

    with app.app_context():
        pool = db.engine.pool

        # Verify pool size is configured
        assert pool.size() == 20

        # Verify pool timeout - default is 30 seconds when SQLALCHEMY_POOL_TIMEOUT is None
        assert pool._timeout == 30

        # Verify pool recycle - default is -1 (disabled) when SQLALCHEMY_POOL_RECYCLE is None
        assert pool._recycle == -1


def test_pool_options_with_custom_values_applied_to_engine(monkeypatch):
    """Integration test: verify custom pool timeout and recycle values are applied to SQLAlchemy engine."""
    from sqlalchemy import create_engine
    from sqlalchemy.pool import QueuePool

    monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)

    settings = Settings(SQLALCHEMY_POOL_TIMEOUT=25, SQLALCHEMY_POOL_RECYCLE=7200)

    # Create engine with custom options using QueuePool (which supports timeout/recycle)
    engine = create_engine("sqlite:///:memory:", poolclass=QueuePool, **settings.SQLALCHEMY_ENGINE_OPTIONS)

    # Verify custom values are applied to the pool
    assert engine.pool._timeout == 25
    assert engine.pool._recycle == 7200
    assert engine.pool.size() == settings.SQLALCHEMY_POOL_SIZE

    engine.dispose()

from pydantic import SecretStr
import pytest
from core.config import Settings


@pytest.fixture
def clear_pool_env_vars(monkeypatch):
    """Fixture to clear SQLAlchemy pool-related environment variables."""
    monkeypatch.delenv("SQLALCHEMY_DATABASE_URI", raising=False)
    monkeypatch.delenv("SQLALCHEMY_POOL_TIMEOUT", raising=False)
    monkeypatch.delenv("SQLALCHEMY_POOL_RECYCLE", raising=False)


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


def test_sqlalchemy_pool_timeout_from_env_var(monkeypatch, clear_pool_env_vars):
    """Test that SQLALCHEMY_POOL_TIMEOUT is correctly read from environment and added to engine options."""
    monkeypatch.setenv("SQLALCHEMY_POOL_TIMEOUT", "666")

    settings = Settings()

    assert settings.SQLALCHEMY_POOL_TIMEOUT == 666
    assert settings.SQLALCHEMY_ENGINE_OPTIONS["pool_timeout"] == 666


def test_sqlalchemy_pool_timeout_from_constructor(clear_pool_env_vars):
    """Test that SQLALCHEMY_POOL_TIMEOUT can be set via constructor and added to engine options."""
    settings = Settings(SQLALCHEMY_POOL_TIMEOUT=25)

    assert settings.SQLALCHEMY_POOL_TIMEOUT == 25
    assert settings.SQLALCHEMY_ENGINE_OPTIONS["pool_timeout"] == 25


def test_sqlalchemy_pool_timeout_not_set(clear_pool_env_vars):
    """Test that SQLALCHEMY_POOL_TIMEOUT is optional and not added to engine options when None."""
    settings = Settings()

    assert settings.SQLALCHEMY_POOL_TIMEOUT is None
    assert "pool_timeout" not in settings.SQLALCHEMY_ENGINE_OPTIONS


def test_sqlalchemy_pool_recycle_from_env_var(monkeypatch, clear_pool_env_vars):
    """Test that SQLALCHEMY_POOL_RECYCLE is correctly read from environment and added to engine options."""
    monkeypatch.setenv("SQLALCHEMY_POOL_RECYCLE", "3600")

    settings = Settings()

    assert settings.SQLALCHEMY_POOL_RECYCLE == 3600
    assert settings.SQLALCHEMY_ENGINE_OPTIONS["pool_recycle"] == 3600


def test_sqlalchemy_pool_recycle_from_constructor(clear_pool_env_vars):
    """Test that SQLALCHEMY_POOL_RECYCLE can be set via constructor and added to engine options."""
    settings = Settings(SQLALCHEMY_POOL_RECYCLE=7200)

    assert settings.SQLALCHEMY_POOL_RECYCLE == 7200
    assert settings.SQLALCHEMY_ENGINE_OPTIONS["pool_recycle"] == 7200


def test_sqlalchemy_pool_recycle_not_set(clear_pool_env_vars):
    """Test that SQLALCHEMY_POOL_RECYCLE is optional and not added to engine options when None."""
    settings = Settings()

    assert settings.SQLALCHEMY_POOL_RECYCLE is None
    assert "pool_recycle" not in settings.SQLALCHEMY_ENGINE_OPTIONS


def test_sqlalchemy_pool_timeout_and_recycle_both_set(clear_pool_env_vars):
    """Test that both SQLALCHEMY_POOL_TIMEOUT and SQLALCHEMY_POOL_RECYCLE are added to engine options."""
    settings = Settings(SQLALCHEMY_POOL_TIMEOUT=666, SQLALCHEMY_POOL_RECYCLE=3600)

    assert settings.SQLALCHEMY_POOL_TIMEOUT == 666
    assert settings.SQLALCHEMY_POOL_RECYCLE == 3600
    assert settings.SQLALCHEMY_ENGINE_OPTIONS["pool_timeout"] == 666
    assert settings.SQLALCHEMY_ENGINE_OPTIONS["pool_recycle"] == 3600


def test_sqlalchemy_engine_options_includes_pool_size_and_max_overflow(clear_pool_env_vars):
    """Test that basic pool size and max overflow are always included in engine options."""
    settings = Settings()

    assert settings.SQLALCHEMY_ENGINE_OPTIONS["pool_size"] == settings.SQLALCHEMY_POOL_SIZE
    assert settings.SQLALCHEMY_ENGINE_OPTIONS["max_overflow"] == settings.SQLALCHEMY_MAX_OVERFLOW


def test_pool_options_applied_to_actual_engine(app):
    """Integration test: verify pool options are applied and engine initializes correctly."""
    from core.managers.db_manager import db

    with app.app_context():
        assert db.engine is not None
        assert db.engine.pool is not None

        assert db.engine.pool.size() == 20


def test_pool_options_with_custom_values_applied_to_engine(monkeypatch, clear_pool_env_vars):
    """Integration test: verify custom pool timeout and recycle values are applied to the engine via app context."""
    monkeypatch.setenv("SQLALCHEMY_POOL_TIMEOUT", "25")
    monkeypatch.setenv("SQLALCHEMY_POOL_RECYCLE", "7200")

    from importlib import reload
    import core.config

    reload(core.config)

    from core import create_app
    from core.managers.db_manager import db
    from core.config import Config

    app = create_app()

    with app.app_context():
        assert Config.SQLALCHEMY_POOL_TIMEOUT == 25
        assert Config.SQLALCHEMY_POOL_RECYCLE == 7200
        assert Config.SQLALCHEMY_ENGINE_OPTIONS["pool_timeout"] == 25
        assert Config.SQLALCHEMY_ENGINE_OPTIONS["pool_recycle"] == 7200

        assert db.engine is not None
        assert db.engine.pool is not None


def test_sqlalchemy_pool_timeout_validation_rejects_zero(clear_pool_env_vars):
    """Test that SQLALCHEMY_POOL_TIMEOUT rejects zero values."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="greater than 0"):
        Settings(SQLALCHEMY_POOL_TIMEOUT=0)


def test_sqlalchemy_pool_timeout_validation_rejects_negative(clear_pool_env_vars):
    """Test that SQLALCHEMY_POOL_TIMEOUT rejects negative values."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="greater than 0"):
        Settings(SQLALCHEMY_POOL_TIMEOUT=-10)


def test_sqlalchemy_pool_recycle_validation_rejects_invalid_negative(clear_pool_env_vars):
    """Test that SQLALCHEMY_POOL_RECYCLE rejects invalid negative values (below -1)."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="greater than or equal to -1"):
        Settings(SQLALCHEMY_POOL_RECYCLE=-2)


def test_sqlalchemy_pool_recycle_accepts_minus_one(clear_pool_env_vars):
    """Test that SQLALCHEMY_POOL_RECYCLE accepts -1 (disabled)."""
    settings = Settings(SQLALCHEMY_POOL_RECYCLE=-1)

    assert settings.SQLALCHEMY_POOL_RECYCLE == -1
    assert settings.SQLALCHEMY_ENGINE_OPTIONS["pool_recycle"] == -1

import os
from pathlib import Path
from typing import Callable

import flask_sqlalchemy.extension
from py_pglite import PGliteConfig
from py_pglite.sqlalchemy import SQLAlchemyPGliteManager
from sqlalchemy.pool import StaticPool


def start_pglite_manager() -> SQLAlchemyPGliteManager:
    configured_work_dir = os.getenv("TARANIS_PGLITE_WORK_DIR")
    work_dir = Path(configured_work_dir) if configured_work_dir else None
    auto_install_deps = work_dir is None

    if work_dir and not (work_dir / "node_modules").exists():
        raise RuntimeError(
            f"PGlite dependencies are missing in '{work_dir}'. "
            "Preinstall them before running tests (see '.github/workflows/linting.yaml' step "
            "'Preinstall PGlite dependencies')."
        )

    manager = SQLAlchemyPGliteManager(
        PGliteConfig(
            auto_install_deps=auto_install_deps,
            cleanup_on_exit=True,
            timeout=60,
            work_dir=work_dir,
        )
    )
    manager.start()
    manager.wait_for_ready()
    return manager


def configure_pglite_environment(manager: SQLAlchemyPGliteManager) -> str:
    uri = manager.get_connection_string()
    os.environ["SQLALCHEMY_DATABASE_URI"] = uri
    return uri


def apply_pglite_engine_options(config) -> None:
    connect_args = {
        **config.SQLALCHEMY_ENGINE_OPTIONS.get("connect_args", {}),
        "application_name": "taranis-core-tests",
        "connect_timeout": 60,
        "prepare_threshold": None,
        "sslmode": "disable",
    }

    engine_options = dict(config.SQLALCHEMY_ENGINE_OPTIONS)
    for key in ("max_overflow", "pool_recycle", "pool_size", "pool_timeout"):
        engine_options.pop(key, None)

    engine_options |= {
        "connect_args": connect_args,
        "pool_pre_ping": False,
        "poolclass": StaticPool,
    }

    config.SQLALCHEMY_ENGINE_OPTIONS = engine_options


def patch_flask_sqlalchemy_engine_creation(
    manager: SQLAlchemyPGliteManager, uri: str
) -> Callable[[], None]:
    original_make_engine = flask_sqlalchemy.extension.SQLAlchemy._make_engine

    def _make_engine(self, bind_key, options, app):
        if str(options.get("url", "")) == uri:
            return manager.get_engine()
        return original_make_engine(self, bind_key, options, app)

    flask_sqlalchemy.extension.SQLAlchemy._make_engine = _make_engine

    def _restore_make_engine() -> None:
        flask_sqlalchemy.extension.SQLAlchemy._make_engine = original_make_engine

    return _restore_make_engine

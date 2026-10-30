import itertools
import json
import os
import uuid
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from flask_jwt_extended import create_access_token

from tests.performance.orm.dataset import Dataset, identifier
from tests.performance.orm.instrumentation import Observations, postgres_connection
from tests.performance.orm.registry import load_manifest, runtime_inventory
from tests.performance.orm.scenarios import scenarios


def pytest_addoption(parser):
    parser.addoption("--orm-profile", default="normal")
    parser.addoption("--orm-path", default="")
    parser.addoption("--orm-pass", choices=("timing", "python", "allocation", "attribution", "control"), default="timing")
    parser.addoption("--orm-pilot", action="store_true")


def pytest_generate_tests(metafunc):
    if "scenario" not in metafunc.fixturenames:
        return
    selected = [item.strip() for item in metafunc.config.getoption("--orm-path").split(",") if item.strip()]
    profiles = metafunc.config.getoption("--orm-profile").split(",")
    phase = metafunc.config.getoption("--orm-pass")
    cases = []
    for profile in profiles:
        for case in scenarios():
            if selected and not any(item in case.id for item in selected):
                continue
            if (case.batch or case.variant != "normal") and profile != "normal":
                continue
            if phase == "allocation" and not (case.operation.startswith("serialize-") or case.paged and case.variant == "normal"):
                continue
            if phase == "control" and case.id not in {
                "assess.stories",
                "analyze.reports",
                "serialization.story",
                "worker.ingest-10",
                "config.organization-create",
            }:
                continue
            cases.append((profile, case))
    metafunc.parametrize("profile,scenario", cases, ids=[f"{profile}-{case.id}" for profile, case in cases])


@dataclass
class Environment:
    app: object
    uri: str
    output: Path
    dataset: Dataset
    headers: dict


@pytest.fixture(scope="session")
def orm_environment(tmp_path_factory, pytestconfig):
    from core import create_app
    from core.config import Config
    from core.managers.db_manager import db
    from core.model.user import User

    uri = os.environ.get("ORM_POSTGRES_URI", "")
    with postgres_connection(uri) as connection:
        assert connection.execute("SHOW server_version_num").fetchone()["server_version_num"].startswith("18")
    output = Path(os.environ["ORM_ARTIFACT_DIR"])
    output.mkdir(parents=True, exist_ok=True)
    settings = {
        "DEBUG": False,
        "SQLALCHEMY_DATABASE_URI": uri,
        "SQLALCHEMY_DATABASE_URI_MASK": "postgresql://profiling",
        "DATA_FOLDER": str(tmp_path_factory.mktemp("orm-data")),
        "REDIS_URL": "redis://redis:6379/0",
        "TARANIS_CORE_SENTRY_DSN": None,
        "OTEL_EXPORTER_OTLP_ENDPOINT": None,
        "SQLALCHEMY_ENGINE_OPTIONS": {
            **Config.SQLALCHEMY_ENGINE_OPTIONS,
            "connect_args": {"connect_timeout": Config.SQLALCHEMY_CONNECT_TIMEOUT},
        },
    }
    with patch.multiple(Config, **settings):
        sequence = itertools.count()
        with (
            Observations(stacks=True) as startup,
            patch("uuid.uuid7", side_effect=lambda: uuid.UUID(identifier(f"bootstrap-{next(sequence)}"))),
        ):
            app = create_app()
        phase = pytestconfig.getoption("--orm-pass")
        (output / f"bootstrap-{phase}.json").write_text(json.dumps(startup.as_dict(), indent=2))
        app.config.update(TESTING=False, PROPAGATE_EXCEPTIONS=False, SERVER_NAME="localhost")
        with app.app_context():
            headers = {"worker": {"Authorization": "Bearer test_key"}, "none": {}}
            snapshot = json.loads((output / "snapshot.json").read_text()) if (output / "snapshot.json").exists() else {}
            for name in ("admin", "user"):
                account = User.find_by_name(snapshot.get("identities", {}).get(name, name))
                assert account is not None
                token = create_access_token(identity=account, expires_delta=timedelta(hours=24))
                headers[name] = {"Authorization": f"Bearer {token}"}
            db.session.remove()
            (output / "inventory.json").write_text(json.dumps(runtime_inventory(app), indent=2))
        dataset = Dataset(app, uri, output)
        yield Environment(app, uri, output, dataset, headers)
        with app.app_context():
            db.session.remove()
            db.engine.dispose()


@pytest.fixture
def prepared_dataset(orm_environment, profile):
    environment = orm_environment
    if environment.dataset.profile != profile:
        environment.dataset.prepare(profile)
    else:
        environment.dataset.restore()
    return environment


@pytest.fixture
def measurement_contract(pytestconfig):
    manifest = load_manifest()
    pilot = pytestconfig.getoption("--orm-pilot")
    return {"rounds": 2 if pilot else manifest["rounds"], "warmups": 1 if pilot else manifest["warmups"]}

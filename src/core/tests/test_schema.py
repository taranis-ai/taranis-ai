import logging
import os
import tempfile
from unittest.mock import patch

import pytest
import schemathesis
from dotenv import load_dotenv
from flask_jwt_extended import create_access_token
from hypothesis import HealthCheck, settings
from pydantic import SecretStr
from schemathesis.checks import CHECKS, load_all_checks
from schemathesis.config import (
    CoveragePhaseConfig,
    ExamplesPhaseConfig,
    GenerationConfig,
    PhasesConfig,
    ProjectConfig,
    ProjectsConfig,
)

from core.__init__ import create_app
from core.config import Config
from core.model.user import User


_APP_FOR_SCHEMA = None


load_dotenv(dotenv_path="tests/.env", override=True)
load_all_checks()

pytestmark = pytest.mark.usefixtures("_bind_schema_app")


def _schema_wsgi_app(environ, start_response):
    if _APP_FOR_SCHEMA is None:
        message = b"Schema app backend not initialized"
        start_response("503 Service Unavailable", [("Content-Type", "text/plain"), ("Content-Length", str(len(message)))])
        return [message]
    return _APP_FOR_SCHEMA(environ, start_response)


_SCHEMA_TEMP_DIR = tempfile.TemporaryDirectory()
_schema_db_uri = f"sqlite:///{_SCHEMA_TEMP_DIR.name}/schema.db"
with (
    patch.dict(os.environ, {"SQLALCHEMY_DATABASE_URI": _schema_db_uri}),
    patch.multiple(Config, SQLALCHEMY_DATABASE_URI=_schema_db_uri, SQLALCHEMY_DATABASE_URI_MASK=_schema_db_uri, QUEUE_ENABLED=False),
):
    _APP_FOR_SCHEMA = create_app(initial_setup=False)


schema_app = _schema_wsgi_app
schemathesis_config = schemathesis.Config(
    projects=ProjectsConfig(
        default=ProjectConfig(
            phases=PhasesConfig(
                examples=ExamplesPhaseConfig(enabled=False),
                coverage=CoveragePhaseConfig(enabled=False),
            ),
            generation=GenerationConfig(modes=[schemathesis.GenerationMode.POSITIVE]),
        )
    )
)
schema = schemathesis.openapi.from_wsgi("/api/static/openapi3_1.yaml", schema_app, config=schemathesis_config).exclude(deprecated=True)


@pytest.fixture(scope="module")
def _bind_schema_app(app):
    global _APP_FOR_SCHEMA
    _APP_FOR_SCHEMA = app
    yield
    _APP_FOR_SCHEMA = None


response_check_names = {
    "not_a_server_error",
    "status_code_conformance",
    "content_type_conformance",
    "response_headers_conformance",
    "response_schema_conformance",
}
response_checks = [check for check in CHECKS.get_all() if check.__name__ in response_check_names]


@schema.auth()
class UserAuth:
    def get(self, case, context):
        with _APP_FOR_SCHEMA.app_context():
            user = User.find_by_name("admin")
            if not user:
                raise AssertionError("Admin user not found")
            return create_access_token(
                identity=user,
                additional_claims={
                    "user_claims": {
                        "id": user.id,
                        "name": user.name,
                        "roles": user.get_roles(),
                    }
                },
            )

    def set(self, case, data, context):
        case.headers = case.headers or {}
        case.headers["Authorization"] = f"Bearer {data}"


def check_401(ctx, response, case):
    if response.status_code == 401:
        raise AssertionError(response.text)


def check_not_401(ctx, response, case):
    if response.status_code != 401:
        raise AssertionError(response.text)


@schema.include(path_regex="^/analyze").parametrize()
@settings(max_examples=20, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_analyze_schema(case):
    response = case.call()
    case.validate_response(response, checks=response_checks, additional_checks=[check_401])


@schema.include(path_regex="^/assess").parametrize()
@settings(max_examples=20, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_assess_schema(case):
    response = case.call()
    case.validate_response(response, checks=response_checks, additional_checks=[check_401])


@schema.auth(UserAuth)
@schema.include(path_regex="^/dashboard").parametrize()
@settings(max_examples=10, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_dashboard_schema(case):
    response = case.call()
    case.validate_response(response, checks=response_checks, additional_checks=[check_401])


@schema.include(path_regex="^/realtime/connect$").parametrize()
@settings(max_examples=2, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_realtime_connect_schema(case, monkeypatch):
    proxy_secret = "schema-test-connect-proxy-secret"
    monkeypatch.setattr(Config, "CENTRIFUGO_CONNECT_PROXY_SECRET", SecretStr(proxy_secret))

    response = case.call(headers={"X-Realtime-Proxy-Key": proxy_secret})
    case.validate_response(response, checks=response_checks)


@schema.include(path_regex=r"^/tasks(?:/|$)").exclude(path="/tasks/user").parametrize()
@settings(max_examples=5, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_worker_task_schema(case, api_header):
    response = case.call(headers=api_header)
    case.validate_response(response, checks=response_checks, additional_checks=[check_401])


@schema.auth(UserAuth)
@schema.include(path_regex=r"^/tasks/user$", method="GET").parametrize()
@settings(max_examples=5, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_user_tasks_schema(case):
    response = case.call()
    case.validate_response(response, checks=response_checks, additional_checks=[check_401])


@schema.include(path_regex=r"^/(?!auth|isalive|health|analyze|assess|assets|worker|bots|tasks|realtime/connect)").parametrize()
@settings(max_examples=2, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_schema_no_auth(case, auth_header_no_permissions, caplog):
    with caplog.at_level(logging.CRITICAL):
        response = case.call(headers=auth_header_no_permissions)
        case.validate_response(response, checks=response_checks, additional_checks=[check_not_401])

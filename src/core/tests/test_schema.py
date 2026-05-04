import logging

import schemathesis
from dotenv import load_dotenv
from flask_jwt_extended import create_access_token
from hypothesis import HealthCheck, settings
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
from core.model.user import User


load_dotenv(dotenv_path="tests/.env", override=True)
load_all_checks()

app = create_app()
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
schema = schemathesis.openapi.from_wsgi("/api/static/openapi3_1.yaml", app, config=schemathesis_config).exclude(deprecated=True)
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
        with context.app.app_context():
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


@schema.include(path_regex=r"^/(?!auth|isalive|health|analyze|assess|assets|worker|bots|tasks)").parametrize()
@settings(max_examples=2, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_schema_no_auth(case, auth_header_no_permissions, caplog):
    with caplog.at_level(logging.CRITICAL):
        response = case.call(headers=auth_header_no_permissions)
        case.validate_response(response, checks=response_checks, additional_checks=[check_not_401])

import schemathesis
import pytest
import logging

logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)
from hypothesis import settings, Verbosity, HealthCheck
from core.__init__ import create_app


app = create_app()
schema = schemathesis.from_wsgi("/api/v1/doc/swagger.json", app)


@schema.parametrize(endpoint="^/api/v1/analyze")
@settings(suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_analyze(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response)


@schema.parametrize(endpoint="^/api/v1/assess/news-items")
@settings(verbosity=Verbosity.debug, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_assess(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response)


@schema.parametrize(endpoint="^/api/v1/auth")
@settings(suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_auth(case):
    response = case.call_wsgi()
    case.validate_response(response)


@schema.parametrize(endpoint="^/api/v1/bots")
@settings(suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_bots(case, api_header):
    response = case.call_wsgi(headers=api_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/v1/collectors")
@settings(suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_collectors(case, api_header):
    response = case.call_wsgi(headers=api_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/v1/config")
@settings(suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_config(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response)


@schema.parametrize(endpoint="^/api/v1/dashboard")
@settings(suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_dashboard(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response)


@schema.parametrize(endpoint="^/api/v1/worker")
@settings(suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_worker(case, api_header):
    response = case.call_wsgi(headers=api_header)
    case.validate_response(response, additional_checks=(check_401,))


# excluded_endpoints = ["analyze", "assess", "assets", "auth", "worker", "bots", "config"]
# excluded_endpoints_regex = f"^(?!/api/v1/{'|/api/v1/'.join(excluded_endpoints)}).*$"


# @schema.parametrize()
# @settings(verbosity=Verbosity.debug)
# def test_schema(case, access_token, client):
#     response = case.call_wsgi(headers={"Authorization": access_token})
#     case.validate_response(response)


def check_401(response, case):
    if response.status_code == 401:
        raise AssertionError(response.text)


def check_not_401(response, case):
    if response.status_code != 401:
        raise AssertionError(response.text)


# @schema.parametrize()
# def test_api_401(case, auth_header_no_permissions):
#     response = case.call_wsgi(headers=auth_header_no_permissions)
#     case.validate_response(response, checks=(check_not_401,))


@pytest.fixture
def state_machine(app, auth_header):
    s = schemathesis.from_wsgi("/api/v1/doc/swagger.json", app)
    s.add_link(
        source=s["/assess/news-items"]["POST"],
        target=s["/assess/news-items/{item_id}"]["GET"],
        status_code="200",
        parameters={"item_id": "$response.body#/id"},
    )

    class APIWorkflow(s.as_state_machine()):
        def get_call_kwargs(self, case):
            return {"headers": auth_header}

        # def after_call(self, response, case):
        #     logger.info(
        #         "%s %s -> %d",
        #         case.method,
        #         case.path,
        #         response.status_code,
        #     )

    return APIWorkflow


def test_schema_stateful(state_machine):
    state_machine.run()

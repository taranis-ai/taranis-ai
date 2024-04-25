import schemathesis
import logging
from dotenv import load_dotenv
from hypothesis import settings, HealthCheck

from core.__init__ import create_app

load_dotenv(dotenv_path="tests/.env", override=True)

app = create_app()
schema = schemathesis.from_wsgi("/api/doc/swagger.json", app, skip_deprecated_operations=True)


def check_401(response, case):
    if response.status_code == 401:
        raise AssertionError(response.text)


def check_not_401(response, case):
    if response.status_code != 401:
        raise AssertionError(response.text)


@schema.parametrize(endpoint="^/api/analyze")
@settings(max_examples=20, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_analyze(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/assess")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_assess(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/dashboard")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_dashboard(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint=r"^/api/(?!auth|isalive)")
@settings(max_examples=2, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_analyze_no_auth(case, auth_header_no_permissions, caplog):
    with caplog.at_level(logging.CRITICAL):
        response = case.call_wsgi(headers=auth_header_no_permissions)
        case.validate_response(response, additional_checks=(check_not_401,))


# @schema.parametrize(endpoint="^/api/worker")
# @settings(suppress_health_check=(HealthCheck.function_scoped_fixture,))
# def test_worker(case, api_header):
#     response = case.call_wsgi(headers=api_header)
#     case.validate_response(response, additional_checks=(check_401,))


# excluded_endpoints = ["analyze", "assess", "assets", "auth", "worker", "bots", "config"]
# excluded_endpoints_regex = f"^(?!/api/{'|/api/'.join(excluded_endpoints)}).*$"


# @schema.parametrize()
# @settings(verbosity=Verbosity.debug)
# def test_schema(case, access_token, client):
#     response = case.call_wsgi(headers={"Authorization": access_token})
#     case.validate_response(response)


# @schema.parametrize()
# def test_api_401(case, auth_header_no_permissions):
#     response = case.call_wsgi(headers=auth_header_no_permissions)
#     case.validate_response(response, checks=(check_not_401,))


# @pytest.fixture
# def state_machine(app, auth_header):
#     s = schemathesis.from_wsgi("/api/doc/swagger.json", app)
#     s.add_link(
#         source=s["/assess/news-items"]["POST"],
#         target=s["/assess/news-items/{item_id}"]["GET"],
#         status_code="200",
#         parameters={"item_id": "$response.body#/id"},
#     )

#     class APIWorkflow(s.as_state_machine()):
#         def get_call_kwargs(self, case):
#             return {"headers": auth_header}

#         # def after_call(self, response, case):
#         #     logger.info(
#         #         "%s %s -> %d",
#         #         case.method,
#         #         case.path,
#         #         response.status_code,
#         #     )

#     return APIWorkflow


# def test_schema_stateful(state_machine):
#     state_machine.run()

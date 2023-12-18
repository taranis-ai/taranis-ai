import schemathesis
import logging
import hypothesis
from hypothesis import settings, HealthCheck
from core.__init__ import create_app

logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)

logger.debug(f"Hypothesis Settings{hypothesis.settings}")

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


@schema.parametrize(endpoint="^/api/config/reload-enum-dictionaries")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_enum(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))

#
# @schema.parametrize(endpoint="^/api/config/reload-enum-dictionaries")
# @settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
# def test_(case, auth_header):
#     response = case.call_wsgi(headers=auth_header)
#     case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/config/attributes")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_attributes(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/config/report-item-types")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_report_items(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/config/product-types")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_product_types(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/config/permissions")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_permissions(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/config/roles")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_roles(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/config/acls")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_acls(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/config/organizations")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_organization(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))

@schema.parametrize(endpoint="^/api/config/users")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_user(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))
    
    
@schema.parametrize(endpoint="^/api/config/workers")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_workers(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/config/worker-types")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_worker_types(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/config/export-word-lists")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_export_word_list(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/config/import-word-lists")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_import_word_list(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/config/word-lists")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_word_lists(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/config/osint-source-groups")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_source_groups(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/config/publisher-preset")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_publisher_preset(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


# @schema.parametrize(endpoint="^/api/config/word-lists")
# @settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
# def test_assess(case, auth_header):
#     response = case.call_wsgi(headers=auth_header)
#     case.validate_response(response, additional_checks=(check_401,))


# TODO: Put off for later
@schema.parametrize(endpoint="^/api/config/parameters")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_parameters(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/config/presenters")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_presenters(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/config/publishers")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_publishers(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/config/bots")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_bots(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


# @schema.parametrize(endpoint="^/api/config/workers")
# @settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
# def test_workers(case, auth_header):
#     response = case.call_wsgi(headers=auth_header)
#     case.validate_response(response, additional_checks=(check_401,))


# TODO: needs revisit = AssertionError
# @schema.parametrize(endpoint="^/api/config/osint-sources")
# @settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
# def test_assess(case, auth_header):
#     response = case.call_wsgi(headers=auth_header)
#     case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/config/export-osint-sources")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_export_osint_sources(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/config/import-osint-sources")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_import_osint_sources(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


@schema.parametrize(endpoint="^/api/config/osint-source-groups")
@settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_osint_source_groups(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response, additional_checks=(check_401,))


# @schema.parametrize(endpoint="^/api/config/publisher-preset")
# @settings(max_examples=50, suppress_health_check=(HealthCheck.function_scoped_fixture,))
# def test_publisher_preset(case, auth_header):
#     response = case.call_wsgi(headers=auth_header)
#     case.validate_response(response, additional_checks=(check_401,))



@schema.parametrize(endpoint="^/api/analyze")
@settings(max_examples=5, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_analyze_no_auth(case, auth_header_no_permissions, caplog):
    with caplog.at_level(logging.CRITICAL):
        response = case.call_wsgi(headers=auth_header_no_permissions)
        case.validate_response(response, additional_checks=(check_not_401,))


@schema.parametrize(endpoint="^/api/assess")
@settings(max_examples=5, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_assess_no_auth(case, auth_header_no_permissions, caplog):
    with caplog.at_level(logging.CRITICAL):
        response = case.call_wsgi(headers=auth_header_no_permissions)
        case.validate_response(response, additional_checks=(check_not_401,))


@schema.parametrize(endpoint="^/api/config/reload-enum-dictionaries")
@settings(max_examples=5, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_enum_no_auth(case, auth_header_no_permissions, caplog):
    with caplog.at_level(logging.CRITICAL):
        response = case.call_wsgi(headers=auth_header_no_permissions)
        case.validate_response(response, additional_checks=(check_not_401,))


@schema.parametrize(endpoint="^/api/config/osint-source-groups")
@settings(max_examples=5, suppress_health_check=(HealthCheck.function_scoped_fixture,))
def test_source_groups_no_auth(case, auth_header_no_permissions, caplog):
    with caplog.at_level(logging.CRITICAL):
        response = case.call_wsgi(headers=auth_header_no_permissions)
        case.validate_response(response, additional_checks=(check_not_401,))


# @schema.parametrize(endpoint="^/api/config/publisher-preset")
# @settings(max_examples=5, suppress_health_check=(HealthCheck.function_scoped_fixture,))
# def test_assess_no_auth(case, auth_header_no_permissions, caplog):
#     with caplog.at_level(logging.CRITICAL):
#         response = case.call_wsgi(headers=auth_header_no_permissions)
#         case.validate_response(response, additional_checks=(check_not_401,))

# @schema.parametrize(endpoint="^/api/dashboard")
# @settings(suppress_health_check=(HealthCheck.function_scoped_fixture,))
# def test_dashboard(case, auth_header):
#     response = case.call_wsgi(headers=auth_header)
#     case.validate_response(response)


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

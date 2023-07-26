import schemathesis
import pytest
from hypothesis import settings, Verbosity
import logging
from schemathesis.checks import *

logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)


@pytest.fixture
def schema_wsgi(app):
    return schemathesis.from_wsgi("/api/v1/doc/swagger.json", app)


schema = schemathesis.from_pytest_fixture("schema_wsgi", validate_schema=True)


@schema.parametrize()
@settings(verbosity=Verbosity.debug)
def test_schema(case, auth_header):
    response = case.call_wsgi(headers=auth_header)
    case.validate_response(response)




@pytest.fixture
def fake_auth_header():
    return {"Authorization": f"Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwibmFtZSI6IlRlc3QifQ.KGms9PM91aSMJJWWSUnzaUalxurP-egFn0tqRutUoUE", "Content-type": "application/json"}


def check_401(response, case):
    if response.status_code != 401:
        raise AssertionError(response.text)


@schema.parametrize()
def test_api_401(case, auth_header_no_permissions):
    response = case.call_wsgi(headers=auth_header_no_permissions)
    case.validate_response(response, checks=(check_401,))


@pytest.fixture
def state_machine(app, auth_header):
    s = schemathesis.from_wsgi("/api/v1/doc/swagger.json", app)
    s.add_link(
        source=s["/assess/news-items"]["POST"],
        target=s["/assess/news-items/{item_id}"]["GET"],
        status_code="200",
        parameters={"item_id": "$response.body#/id"}
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


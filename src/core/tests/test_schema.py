import schemathesis
import pytest


@pytest.fixture
def schema_wsgi(app):
    return schemathesis.from_wsgi("/api/v1/doc/swagger.json", app)


schema = schemathesis.from_pytest_fixture("schema_wsgi")


@schema.parametrize()
def test_schema(case, access_token, client):
    response = case.call_wsgi(headers={"Authorization": access_token})
    case.validate_response(response)

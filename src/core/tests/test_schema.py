import schemathesis
import pytest
from hypothesis import settings, Verbosity


@pytest.fixture
def schema_wsgi(app):
    return schemathesis.from_wsgi("/api/v1/doc/swagger.json", app)


schema = schemathesis.from_pytest_fixture("schema_wsgi", validate_schema=True)


@schema.parametrize()
@settings(verbosity=Verbosity.debug)
def test_schema(case, access_token, client):
    response = case.call_wsgi(headers={"Authorization": access_token})
    case.validate_response(response)

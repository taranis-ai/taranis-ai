import schemathesis
from hypothesis import settings, HealthCheck

schema = schemathesis.from_uri("http://127.0.0.1:5000/api/v1/doc/swagger.json")


# @schema.parametrize(endpoint="/api/v1/analyze")
# @settings(max_examples=100, suppress_health_check=[HealthCheck.filter_too_much])
# def test_schema_analyze(case, access_token):
#     case.call_and_validate(headers={"Authorization": access_token})


@schema.parametrize(endpoint="/api/v1/assess")
def test_schema_assess(case, access_token):
    case.call_and_validate(headers={"Authorization": access_token})


@schema.parametrize(endpoint="/api/v1/config/users")
def test_schema_users(case, access_token):
    case.call_and_validate(headers={"Authorization": access_token})


@schema.parametrize(endpoint="/api/v1/config/organizations")
def test_schema_organizations(case, access_token):
    case.call_and_validate(headers={"Authorization": access_token})


@schema.parametrize(endpoint="/api/v1/config/osint-source-groups")
def test_schema_osint_source_groups(case, access_token):
    case.call_and_validate(headers={"Authorization": access_token})


@schema.parametrize(endpoint="/api/v1/config/osint-sources")
def test_schema_osint_sources(case, access_token):
    case.call_and_validate(headers={"Authorization": access_token})


@schema.parametrize(endpoint="/api/v1/config/product-types")
def test_schema_product_types(case, access_token):
    case.call_and_validate(headers={"Authorization": access_token})


@schema.parametrize(endpoint="/api/v1/config/publisher-preset")
def test_schema_publisher_presets(case, access_token):
    case.call_and_validate(headers={"Authorization": access_token})


@schema.parametrize(endpoint="/api/v1/config/report-item-types")
def test_schema_report_item_types(case, access_token):
    case.call_and_validate(headers={"Authorization": access_token})


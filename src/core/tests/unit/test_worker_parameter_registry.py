import pytest
from models.types import WORKER_TYPES
from models.worker_parameters import (
    effective_parameter_values,
    normalize_parameter_values,
    parameter_schema,
)
from pydantic import ValidationError


def test_schema_preserves_contract_order_and_frontend_metadata():
    schema = parameter_schema("RSS_COLLECTOR")

    assert list(schema["properties"])[-4:] == [
        "FEED_URL",
        "CONTENT_LOCATION",
        "USE_FEED_CONTENT",
        "XPATH",
    ]
    assert schema["properties"]["FEED_URL"]["title"] == "Feed URL"
    assert schema["properties"]["FEED_URL"]["description"]
    assert schema["properties"]["REFRESH_INTERVAL"]["widget"] == "cron"
    assert schema["properties"]["USE_GLOBAL_PROXY"]["type"] == "boolean"


def test_boundary_adapter_uses_canonical_strings():
    configured = normalize_parameter_values(
        "RSS_COLLECTOR",
        {"FEED_URL": "https://example.test/feed", "USE_GLOBAL_PROXY": "on", "ADDITIONAL_HEADERS": '{"X-B":"2","X-A":"1"}'},
    )

    assert configured == {
        "FEED_URL": "https://example.test/feed",
        "USE_GLOBAL_PROXY": "true",
        "ADDITIONAL_HEADERS": '{"X-A":"1","X-B":"2"}',
    }


def test_effective_values_expand_defaults_and_unknown_fields_are_rejected():
    effective = effective_parameter_values("RSS_COLLECTOR", {"FEED_URL": "https://example.test/feed"})
    assert effective["USE_GLOBAL_PROXY"] == "false"
    assert effective["REFRESH_INTERVAL"] == ""

    with pytest.raises(ValidationError):
        effective_parameter_values("RSS_COLLECTOR", {"FEED_URL": "x", "UNKNOWN": "value"})


def test_secret_schema_uses_standard_password_fields():
    schema = parameter_schema("MISP_CONNECTOR")
    api_key = schema["properties"]["API_KEY"]

    assert api_key["format"] == "password"
    assert api_key["writeOnly"] is True


def test_every_schema_uses_uppercase_names_and_documents_each_field():
    for worker_type in WORKER_TYPES:
        for name, field_schema in parameter_schema(worker_type).get("properties", {}).items():
            assert name == name.upper()
            assert field_schema.get("title")
            assert field_schema.get("description")


@pytest.mark.parametrize(
    ("worker_type", "parameters"),
    [
        ("RSS_COLLECTOR", {"FEED_URL": "feed", "REFRESH_INTERVAL": "not-a-cron"}),
        ("RSS_COLLECTOR", {"FEED_URL": "feed", "TLP_LEVEL": "blue"}),
        ("RSS_COLLECTOR", {"FEED_URL": "feed", "ADDITIONAL_HEADERS": "[]"}),
        ("NLP_BOT", {"REQUESTS_TIMEOUT": "0"}),
        (
            "TAXII_PUBLISHER",
            {"TAXII_COLLECTION_ID": "collection", "AUTH_TYPE": "token", "API_TOKEN": ""},
        ),
    ],
)
def test_intrinsic_and_cross_field_validation(worker_type, parameters):
    with pytest.raises(ValidationError):
        effective_parameter_values(worker_type, parameters)


def test_runtime_parameter_names_are_part_of_the_authoritative_contract():
    tagging = parameter_schema("TAGGING_BOT")["properties"]
    wordlist = parameter_schema("WORDLIST_BOT")["properties"]

    assert "REGULAR_EXPRESSION" in tagging
    assert "KEYWORDS" not in tagging
    assert {"IGNORECASE", "OVERRIDE_EXISTING_TAGS"} <= set(wordlist)

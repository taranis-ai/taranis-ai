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


def test_boundary_adapter_preserves_native_values():
    configured = normalize_parameter_values(
        "RSS_COLLECTOR",
        {
            "FEED_URL": "https://example.test/feed",
            "USE_GLOBAL_PROXY": "on",
            "ADDITIONAL_HEADERS": '{"X-B":"2","X-A":"1"}',
            "DIGEST_SPLITTING_LIMIT": "10",
        },
    )

    assert configured == {
        "FEED_URL": "https://example.test/feed",
        "USE_GLOBAL_PROXY": True,
        "ADDITIONAL_HEADERS": {"X-A": "1", "X-B": "2"},
        "DIGEST_SPLITTING_LIMIT": 10,
    }


def test_effective_values_expand_defaults_and_unknown_fields_are_rejected():
    effective = effective_parameter_values("RSS_COLLECTOR", {"FEED_URL": "https://example.test/feed"})
    assert effective["USE_GLOBAL_PROXY"] is False
    assert effective["REFRESH_INTERVAL"] == ""

    with pytest.raises(ValidationError):
        effective_parameter_values("RSS_COLLECTOR", {"FEED_URL": "x", "UNKNOWN": "value"})


def test_secret_schema_uses_standard_password_fields():
    schema = parameter_schema("MISP_CONNECTOR")
    api_key = schema["properties"]["API_KEY"]

    assert api_key["format"] == "password"
    assert api_key["writeOnly"] is True


def test_mastodon_timeline_contract_and_secret():
    schema = parameter_schema("MASTODON_COLLECTOR")
    assert schema["properties"]["TIMELINE"]["enum"] == ["hashtag", "home", "account"]
    assert schema["properties"]["ACCESS_TOKEN"]["format"] == "password"
    assert schema["properties"]["ACCESS_TOKEN"]["writeOnly"] is True

    hashtag = effective_parameter_values(
        "MASTODON_COLLECTOR",
        {"INSTANCE_URL": "https://mastodon.example", "TIMELINE": "hashtag", "HASHTAG": "security"},
    )
    assert hashtag["ACCESS_TOKEN"] == ""

    for parameters in (
        {"INSTANCE_URL": "https://mastodon.example", "TIMELINE": "hashtag"},
        {"INSTANCE_URL": "https://mastodon.example", "TIMELINE": "home"},
        {"INSTANCE_URL": "https://mastodon.example", "TIMELINE": "account", "ACCOUNT": "alice"},
    ):
        with pytest.raises(ValidationError):
            effective_parameter_values("MASTODON_COLLECTOR", parameters)

    account = effective_parameter_values(
        "MASTODON_COLLECTOR",
        {
            "INSTANCE_URL": "https://mastodon.example",
            "TIMELINE": "account",
            "ACCOUNT": "alice@example.social",
            "ACCESS_TOKEN": "secret",
        },
    )
    assert account["ACCESS_TOKEN"] == "secret"

    for invalid_parameters in (
        {"INSTANCE_URL": "https://user:password@mastodon.example", "TIMELINE": "hashtag", "HASHTAG": "security"},
        {"INSTANCE_URL": "https://mastodon.example/api", "TIMELINE": "hashtag", "HASHTAG": "security"},
        {"INSTANCE_URL": "https://mastodon.example", "TIMELINE": "hashtag", "HASHTAG": "threat intel"},
        {"INSTANCE_URL": "https://mastodon.example", "TIMELINE": "hashtag", "HASHTAG": "security?limit=100"},
        {
            "INSTANCE_URL": "https://mastodon.example",
            "TIMELINE": "account",
            "ACCOUNT": "https://mastodon.example/@alice",
            "ACCESS_TOKEN": "secret",
        },
    ):
        with pytest.raises(ValidationError):
            effective_parameter_values("MASTODON_COLLECTOR", invalid_parameters)


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
            {"TAXII_COLLECTION_ID": "collection", "AUTH_TYPE": "bearer", "API_TOKEN": ""},
        ),
        (
            "KAFKA_PUBLISHER",
            {
                "KAFKA_TOPIC": "topic",
                "KAFKA_BOOTSTRAP_SERVERS": "kafka:9092",
                "KAFKA_SECURITY_PROTOCOL": "SASL_SSL",
            },
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


def test_taxii_bearer_auth_matches_the_worker_contract():
    effective = effective_parameter_values(
        "TAXII_PUBLISHER",
        {
            "TAXII_API_ROOT_URL": "https://taxii.example.test/root",
            "TAXII_COLLECTION_ID": "collection",
            "AUTH_TYPE": "bearer",
            "API_TOKEN": "secret",
        },
    )

    assert effective["AUTH_TYPE"] == "bearer"
    assert effective["API_TOKEN"] == "secret"


def test_kafka_security_protocols_match_worker_contract():
    protocols = ["PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"]
    assert parameter_schema("KAFKA_PUBLISHER")["properties"]["KAFKA_SECURITY_PROTOCOL"]["enum"] == protocols

    for security_protocol in protocols:
        parameters = {
            "KAFKA_TOPIC": "topic",
            "KAFKA_BOOTSTRAP_SERVERS": "kafka:9092",
            "KAFKA_SECURITY_PROTOCOL": security_protocol,
            "KAFKA_SASL_MECHANISM": "PLAIN",
            "KAFKA_SASL_USERNAME": "user",
            "KAFKA_SASL_PASSWORD": "secret",
        }
        assert effective_parameter_values("KAFKA_PUBLISHER", parameters)["KAFKA_SECURITY_PROTOCOL"] == security_protocol

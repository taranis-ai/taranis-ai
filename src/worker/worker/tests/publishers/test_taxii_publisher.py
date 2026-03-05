import json

import pytest

from worker.tests.publishers.publishers_data import product_text


class MockProduct:
    def __init__(self, data, mime_type):
        self.data = data
        self.mime_type = mime_type


class FakeCollection:
    def __init__(self):
        self.sent_envelopes = []

    def add_objects(self, envelope):
        self.sent_envelopes.append(envelope)
        return {"id": "status--1", "status": "complete"}


def _bundle_product() -> MockProduct:
    payload = {
        "type": "bundle",
        "id": "bundle--00000000-0000-4000-8000-000000000001",
        "spec_version": "2.1",
        "objects": [
            {
                "type": "indicator",
                "spec_version": "2.1",
                "id": "indicator--00000000-0000-4000-8000-000000000001",
                "created": "2026-01-01T00:00:00.000Z",
                "modified": "2026-01-01T00:00:00.000Z",
                "pattern": "[ipv4-addr:value = '203.0.113.10']",
                "pattern_type": "stix",
                "valid_from": "2026-01-01T00:00:00.000Z",
            }
        ],
    }
    return MockProduct(data=json.dumps(payload).encode("utf-8"), mime_type="application/json")


def test_taxii_publisher_publish_sends_bundle_objects(taxii_publisher, monkeypatch):
    fake_collection = FakeCollection()
    monkeypatch.setattr(taxii_publisher, "_get_collection", lambda _: fake_collection)

    publisher_data = {
        "parameters": {
            "TAXII_API_ROOT_URL": "https://taxii.example/api/root/",
            "TAXII_COLLECTION_ID": "collection-1",
            "AUTH_TYPE": "basic",
            "USERNAME": "alice",
            "PASSWORD": "secret",
        }
    }

    result = taxii_publisher.publish(publisher_data, product_text, _bundle_product())

    assert result["status"] == "success"
    assert result["objects_sent"] == 1
    assert fake_collection.sent_envelopes[0]["objects"][0]["type"] == "indicator"


def test_taxii_publisher_rejects_non_bundle_payload(taxii_publisher):
    publisher_data = {
        "parameters": {
            "TAXII_API_ROOT_URL": "https://taxii.example/api/root/",
            "TAXII_COLLECTION_ID": "collection-1",
            "AUTH_TYPE": "basic",
            "USERNAME": "alice",
            "PASSWORD": "secret",
        }
    }

    rendered_product = MockProduct(data=json.dumps([{"type": "indicator"}]).encode("utf-8"), mime_type="application/json")

    with pytest.raises(ValueError, match="Rendered product must be a STIX bundle"):
        taxii_publisher.publish(publisher_data, product_text, rendered_product)


def test_taxii_publisher_requires_token_for_bearer_auth(taxii_publisher):
    publisher_data = {
        "parameters": {
            "TAXII_API_ROOT_URL": "https://taxii.example/api/root/",
            "TAXII_COLLECTION_ID": "collection-1",
            "AUTH_TYPE": "bearer",
        }
    }

    with pytest.raises(ValueError, match="AUTH_TYPE bearer requires API_TOKEN"):
        taxii_publisher.publish(publisher_data, product_text, _bundle_product())


def test_taxii_publisher_requires_username_password_for_basic_auth(taxii_publisher):
    publisher_data = {
        "parameters": {
            "TAXII_API_ROOT_URL": "https://taxii.example/api/root/",
            "TAXII_COLLECTION_ID": "collection-1",
            "AUTH_TYPE": "basic",
            "USERNAME": "alice",
        }
    }

    with pytest.raises(ValueError, match="AUTH_TYPE basic requires USERNAME and PASSWORD"):
        taxii_publisher.publish(publisher_data, product_text, _bundle_product())

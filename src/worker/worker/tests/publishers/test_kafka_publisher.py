import json

import pytest

from worker.publishers.kafka_publisher import KafkaPublisher
from worker.tests.publishers.publishers_data import product_text


class FakeKafkaProducer:
    def __init__(self):
        self.produce_calls = []
        self.flush_calls = []

    def produce(self, topic, key=None, value=None):
        self.produce_calls.append(
            {
                "topic": topic,
                "key": key,
                "value": value,
            }
        )

    def flush(self, timeout=None):
        self.flush_calls.append({"timeout": timeout})
        return 0


def test_kafka_publisher_publish_sends_product_to_topic(
    kafka_publisher_testdata,
    get_product_mock,
):
    producer = FakeKafkaProducer()
    publisher = KafkaPublisher(producer=producer)

    result = publisher.publish(
        kafka_publisher_testdata,
        product_text,
        get_product_mock,
    )

    assert result["status"] == "success"

    topic = kafka_publisher_testdata["parameters"]["KAFKA_TOPIC"]

    assert len(producer.produce_calls) == 1
    produce_call = producer.produce_calls[0]

    assert produce_call["topic"] == topic
    assert produce_call["key"] == result["key"].encode("utf-8")
    assert result["key"].startswith(product_text["title"])

    message = json.loads(produce_call["value"].decode("utf-8"))

    assert message["object_name"] == result["key"]
    assert message["object_name"].startswith(product_text["title"])
    assert message["mime_type"] == get_product_mock.mime_type
    assert message["data"] == get_product_mock.data.decode("utf-8")
    assert message["product"] == product_text

    assert producer.flush_calls == [{"timeout": float(kafka_publisher_testdata["parameters"]["KAFKA_SEND_TIMEOUT"])}]

    assert result["topic"] == topic
    assert result["key"] == produce_call["key"].decode("utf-8")
    assert result["message"] == f"Product {result['key']} published to Kafka topic {topic}."


def test_kafka_publisher_create_producer_with_sasl_plaintext(monkeypatch):
    captured_config = {}

    class FakeProducer:
        def __init__(self, config):
            captured_config.update(config)

    monkeypatch.setattr(
        "worker.publishers.kafka_publisher.Producer",
        FakeProducer,
    )

    parameters = {
        "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
        "KAFKA_TOPIC": "test-topic",
        "KAFKA_SECURITY_PROTOCOL": "SASL_PLAINTEXT",
        "KAFKA_SASL_MECHANISM": "PLAIN",
        "KAFKA_SASL_USERNAME": "user",
        "KAFKA_SASL_PASSWORD": "password",
    }

    KafkaPublisher._create_producer(parameters)

    assert captured_config["bootstrap.servers"] == "localhost:9092"
    assert captured_config["security.protocol"] == "SASL_PLAINTEXT"
    assert captured_config["sasl.mechanism"] == "PLAIN"
    assert captured_config["sasl.username"] == "user"
    assert captured_config["sasl.password"] == "password"


def test_kafka_publisher_create_producer_sasl_requires_credentials():
    parameters = {
        "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
        "KAFKA_TOPIC": "test-topic",
        "KAFKA_SECURITY_PROTOCOL": "SASL_PLAINTEXT",
    }

    with pytest.raises(ValueError, match="parameters are missing"):
        KafkaPublisher._create_producer(parameters)

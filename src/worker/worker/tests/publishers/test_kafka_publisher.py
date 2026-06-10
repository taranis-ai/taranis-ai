import json

import pytest

from worker.publishers.kafka_publisher import KafkaPublisher
from worker.tests.publishers.publishers_data import product_text


class FakeKafkaProducer:
    def __init__(self, *, produce_error=None, delivery_error=None):
        self.produce_calls = []
        self.flush_calls = []
        self.produce_error = produce_error
        self.delivery_error = delivery_error

    def produce(self, topic, key=None, value=None, on_delivery=None):
        if self.produce_error is not None:
            raise self.produce_error
        self.produce_calls.append(
            {
                "topic": topic,
                "key": key,
                "value": value,
            }
        )
        self.on_delivery = on_delivery

    def flush(self, timeout=None):
        self.flush_calls.append({"timeout": timeout})
        if hasattr(self, "on_delivery") and self.on_delivery is not None:
            self.on_delivery(self.delivery_error, object())
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


def test_kafka_publisher_create_producer_uses_defaults_for_empty_optional_parameters(monkeypatch):
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
        "KAFKA_SECURITY_PROTOCOL": "",
        "KAFKA_ACKS": "",
        "KAFKA_RETRIES": "",
    }

    KafkaPublisher._create_producer(parameters)

    assert captured_config["security.protocol"] == "PLAINTEXT"
    assert captured_config["acks"] == "all"
    assert captured_config["retries"] == 3


def test_kafka_publisher_publish_raises_on_produce_buffer_error(
    kafka_publisher_testdata,
    get_product_mock,
):
    producer = FakeKafkaProducer(produce_error=BufferError("queue full"))
    publisher = KafkaPublisher(producer=producer)

    with pytest.raises(RuntimeError, match="Failed to queue Kafka message"):
        publisher.publish(
            kafka_publisher_testdata,
            product_text,
            get_product_mock,
        )


def test_kafka_publisher_publish_raises_on_delivery_error(
    kafka_publisher_testdata,
    get_product_mock,
):
    producer = FakeKafkaProducer(delivery_error="broker unavailable")
    publisher = KafkaPublisher(producer=producer)

    with pytest.raises(RuntimeError, match="Kafka delivery failed"):
        publisher.publish(
            kafka_publisher_testdata,
            product_text,
            get_product_mock,
        )

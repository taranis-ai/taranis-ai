import json
from typing import Any

from kafka import KafkaProducer
from models.product import WorkerProduct as Product

from .base_publisher import BasePublisher


class KafkaPublisher(BasePublisher):
    REQUIRED_PARAMETERS = (
        "KAFKA_BOOTSTRAP_SERVERS",
        "KAFKA_TOPIC",
    )

    def __init__(self, producer=None):
        super().__init__()
        self.type = "KAFKA_PUBLISHER"
        self.name = "Kafka Publisher"
        self.description = "Publisher for publishing products to a Kafka topic"
        self.producer = producer

    def publish(
        self,
        publisher: dict[str, Any],
        product: dict[str, Any],
        rendered_product: Product,
    ):
        parameters = self._extract_parameters(publisher)
        producer = self.producer or self._create_producer(parameters)

        topic = parameters["KAFKA_TOPIC"]
        key = BasePublisher.get_file_name(product)

        message = self._create_message(
            product=product,
            rendered_product=rendered_product,
            object_name=key,
        )

        future = producer.send(
            topic=topic,
            key=key,
            value=message,
        )

        record_metadata = future.get(timeout=parameters.get("KAFKA_SEND_TIMEOUT", 30))

        producer.flush()

        return {
            "status": "success",
            "topic": record_metadata.topic,
            "partition": record_metadata.partition,
            "offset": record_metadata.offset,
            "key": key,
            "message": f"Product {key} published to Kafka topic {topic}.",
        }

    @staticmethod
    def _create_producer(parameters: dict[str, Any]) -> KafkaProducer:
        security_protocol = str(parameters.get("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")).upper()

        if security_protocol not in {"PLAINTEXT", "SASL_PLAINTEXT"}:
            raise ValueError("Invalid KAFKA_SECURITY_PROTOCOL. Only 'PLAINTEXT' and 'SASL_PLAINTEXT' are supported.")

        producer_config = {
            "bootstrap_servers": parameters["KAFKA_BOOTSTRAP_SERVERS"],
            "client_id": parameters.get("KAFKA_CLIENT_ID", "worker-kafka-publisher"),
            "key_serializer": lambda key: key.encode("utf-8"),
            "value_serializer": lambda value: json.dumps(value).encode("utf-8"),
            "acks": parameters.get("KAFKA_ACKS", "all"),
            "retries": int(parameters.get("KAFKA_RETRIES", 3)),
            "security_protocol": security_protocol,
        }

        if security_protocol == "SASL_PLAINTEXT":
            missing = [
                parameter
                for parameter in (
                    "KAFKA_SASL_MECHANISM",
                    "KAFKA_SASL_USERNAME",
                    "KAFKA_SASL_PASSWORD",
                )
                if not parameters.get(parameter)
            ]

            if missing:
                raise ValueError(f"KAFKA_SECURITY_PROTOCOL is 'SASL_PLAINTEXT', but these parameters are missing: {', '.join(missing)}")

            producer_config.update(
                {
                    "sasl_mechanism": parameters["KAFKA_SASL_MECHANISM"],
                    "sasl_plain_username": parameters["KAFKA_SASL_USERNAME"],
                    "sasl_plain_password": parameters["KAFKA_SASL_PASSWORD"],
                }
            )

        return KafkaProducer(**producer_config)

    @staticmethod
    def _create_message(
        product: dict[str, Any],
        rendered_product: Product,
        object_name: str,
    ) -> dict[str, Any]:
        return {
            "object_name": object_name,
            "mime_type": rendered_product.mime_type,
            "data": rendered_product.data.decode("utf-8"),
            "product": product,
        }

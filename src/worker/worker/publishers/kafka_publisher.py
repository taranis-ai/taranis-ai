import json
from typing import Any

from confluent_kafka import Producer
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
        delivery_result: dict[str, str | None] = {"error": None}

        def on_delivery(err, msg):
            if err is not None:
                delivery_result["error"] = str(err)

        try:
            producer.produce(
                topic=topic,
                key=key.encode("utf-8"),
                value=json.dumps(message).encode("utf-8"),
                on_delivery=on_delivery,
            )
        except BufferError as exc:
            raise RuntimeError(f"Failed to queue Kafka message for topic {topic}: {exc}") from exc

        producer.flush(timeout=float(parameters.get("KAFKA_SEND_TIMEOUT") or 30))
        if delivery_result["error"] is not None:
            raise RuntimeError(f"Kafka delivery failed for topic {topic}: {delivery_result['error']}")

        return {
            "status": "success",
            "topic": topic,
            "key": key,
            "message": f"Product {key} published to Kafka topic {topic}.",
        }

    @staticmethod
    def _create_producer(parameters: dict[str, Any]) -> Producer:
        security_protocol = str(parameters.get("KAFKA_SECURITY_PROTOCOL") or "PLAINTEXT").upper()

        if security_protocol not in {"PLAINTEXT", "SASL_PLAINTEXT"}:
            raise ValueError("Invalid KAFKA_SECURITY_PROTOCOL. Only 'PLAINTEXT' and 'SASL_PLAINTEXT' are supported.")

        producer_config = {
            "bootstrap.servers": parameters["KAFKA_BOOTSTRAP_SERVERS"],
            "client.id": "taranis-kafka-publisher",
            "acks": parameters.get("KAFKA_ACKS") or "all",
            "retries": int(parameters.get("KAFKA_RETRIES") or 3),
            "security.protocol": security_protocol,
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

            producer_config |= {
                "sasl.mechanism": parameters["KAFKA_SASL_MECHANISM"],
                "sasl.username": parameters["KAFKA_SASL_USERNAME"],
                "sasl.password": parameters["KAFKA_SASL_PASSWORD"],
            }

        return Producer(producer_config)

    @staticmethod
    def _create_message(
        product: dict[str, Any],
        rendered_product: Product,
        object_name: str,
    ) -> dict[str, Any]:
        return {"object_name": object_name, "mime_type": rendered_product.mime_type, "data": rendered_product.data.decode("ascii")}

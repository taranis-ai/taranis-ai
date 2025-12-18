from io import BytesIO
from typing import Any

from minio import Minio

from worker.types import Product

from .base_publisher import BasePublisher


class S3Publisher(BasePublisher):
    REQUIRED_PARAMETERS = ("S3_ENDPOINT", "S3_ACCESS_KEY", "S3_SECRET_KEY", "S3_BUCKET_NAME")

    def __init__(self, client=None):
        super().__init__()
        self.type = "S3_PUBLISHER"
        self.name = "S3 Publisher"
        self.description = "Publisher for publishing to S3 compatible storage"
        self.client = client

    def publish(self, publisher: dict[str, Any], product: dict[str, Any], rendered_product: Product):
        parameters = self._extract_parameters(publisher)
        client = self.client or self._create_client(parameters)

        bucket_name = parameters["S3_BUCKET_NAME"]
        bucket_name, path = bucket_name.split("/")[0], "/".join(bucket_name.split("/")[1:])
        self._ensure_bucket(client, bucket_name)
        object_name = f"{path}/{BasePublisher.get_file_name(product)}"
        self._upload_object(client, bucket_name, object_name, rendered_product)

        return {"status": "success", "object_name": object_name, "message": f"File {object_name} uploaded to bucket {bucket_name}."}

    @staticmethod
    def _create_client(parameters: dict[str, Any]) -> Minio:
        return Minio(
            endpoint=parameters["S3_ENDPOINT"],
            access_key=parameters["S3_ACCESS_KEY"],
            secret_key=parameters["S3_SECRET_KEY"],
            session_token=parameters.get("S3_SESSION_TOKEN"),
            region=parameters.get("S3_REGION"),
            secure=parameters.get("S3_SECURE", True),
            cert_check=parameters.get("S3_CERT_CHECK", True),
        )

    @staticmethod
    def _ensure_bucket(client: Minio, bucket_name: str) -> None:
        if not client.bucket_exists(bucket_name=bucket_name):
            client.make_bucket(bucket_name=bucket_name)

    @staticmethod
    def _upload_object(client: Minio, bucket_name: str, object_name: str, rendered_product: Product) -> None:
        client.put_object(
            bucket_name=bucket_name,
            data=BytesIO(rendered_product.data),
            object_name=object_name,
            length=len(rendered_product.data),
            content_type=rendered_product.mime_type,
        )

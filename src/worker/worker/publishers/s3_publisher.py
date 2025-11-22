from io import BytesIO
from typing import Any

from minio import Minio

from worker.types import Product

from .base_publisher import BasePublisher


class S3Publisher(BasePublisher):
    def __init__(self):
        super().__init__()
        self.type = "S3_PUBLISHER"
        self.name = "S3 Publisher"
        self.description = "Publisher for publishing to S3 compatible storage"

    def publish(self, publisher: dict[str, Any], product: dict[str, Any], rendered_product: Product):
        parameters = publisher.get("parameters", {})

        endponit = parameters.get("S3_ENDPOINT")
        access_key = parameters.get("S3_ACCESS_KEY")
        secret_key = parameters.get("S3_SECRET_KEY")
        bucket_name = parameters.get("S3_BUCKET_NAME")
        session_token = parameters.get("S3_SESSION_TOKEN")
        region = parameters.get("S3_REGION")
        secure = parameters.get("S3_SECURE", True)
        cert_check = parameters.get("S3_CERT_CHECK", True)

        if not all([endponit, access_key, secret_key, bucket_name]):
            raise ValueError("S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY and S3_BUCKET_NAME are required parameters for S3 Publisher")

        self.set_file_name(product)
        client = Minio(
            endpoint=endponit,
            access_key=access_key,
            secret_key=secret_key,
            session_token=session_token,
            region=region,
            secure=secure,
            cert_check=cert_check,
        )

        client.put_object(
            bucket_name=bucket_name,
            data=BytesIO(rendered_product.data),
            object_name=self.file_name,
            length=len(rendered_product.data),
            content_type=rendered_product.mime_type,
        )

        return {"status": "success", "message": f"File {self.file_name} uploaded to bucket {bucket_name}."}

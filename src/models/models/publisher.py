from pydantic import BaseModel, Field


class PublisherTaskRequest(BaseModel):
    product_id: str = Field(..., description="ID of the product to publish")
    publisher_id: str = Field(..., description="ID of the publisher")

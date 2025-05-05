from pydantic import BaseModel, Field
from prefect import flow, task
from core.log import logger


class PublisherTaskRequest(BaseModel):
    product_id: str = Field(..., description="ID of the product to publish")
    publisher_id: str = Field(..., description="ID of the publisher")


@task
def run_publisher_logic(request: PublisherTaskRequest):
    # TODO: implement publishing logic
    logger.info(f"[publisher_task] Publishing product {request.product_id} with publisher {request.publisher_id}")


@flow(name="publisher-task-flow")
def publisher_task_flow(request: PublisherTaskRequest):
    run_publisher_logic(request)

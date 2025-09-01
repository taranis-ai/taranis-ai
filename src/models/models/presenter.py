from pydantic import BaseModel, Field
from typing import Optional


class PresenterTaskRequest(BaseModel):
    product_id: str = Field(..., description="ID of the product to generate")
    countdown: Optional[int] = Field(default=0, description="Optional countdown (in seconds) before execution")

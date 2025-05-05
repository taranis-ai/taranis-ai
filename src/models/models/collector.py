from pydantic import BaseModel, Field


class CollectorTaskRequest(BaseModel):
    source_id: str = Field(..., description="ID of the OSINT source to collect from")
    preview: bool = Field(False, description="Whether this is a preview collection or full")

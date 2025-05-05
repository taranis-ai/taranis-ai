from pydantic import BaseModel, Field
from typing import Optional, List


class ConnectorTaskRequest(BaseModel):
    connector_id: str = Field(..., description="ID of the connector to run")
    story_ids: Optional[List[str]] = Field(default=None, description="Optional list of story IDs to push to the connector")

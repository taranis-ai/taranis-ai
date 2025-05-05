from pydantic import BaseModel, Field
from typing import Optional, Dict


class BotTaskRequest(BaseModel):
    bot_id: int = Field(..., description="ID of the bot to execute")
    filter: Optional[Dict[str, str]] = Field(default=None, description="Optional filters to apply before execution")

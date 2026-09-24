from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


LLM_FEATURES = {"chat": "Chat", "clustering": "Story clustering", "summarization": "Summarization and titles"}


class LLMEndpoint(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    base_url: str = Field(min_length=1)
    model: str = ""
    api_format: Literal["responses", "chat_completions"] = "responses"
    api_key: str = Field(default="", repr=False)
    timeout: int = Field(default=120, gt=0)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Enter an HTTP or HTTPS provider base URL without credentials")
        if parsed.port == 0 or parsed.query or parsed.fragment or parsed.path.rstrip("/").endswith(("/responses", "/chat/completions")):
            raise ValueError("Enter the provider base URL without an API endpoint, query, or fragment")
        return value.rstrip("/")

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


LLM_FEATURES = {
    "chat": "Chat",
    "clustering": "Story clustering",
    "summarization": "Summarization and titles",
    "ner": "Named-entity recognition",
    "sentiment": "Sentiment analysis",
    "classification": "Cybersecurity classification",
}


LLM_BOT_FEATURES = {
    "story_bot": "clustering",
    "summary_bot": "summarization",
    "nlp_bot": "ner",
    "sentiment_analysis_bot": "sentiment",
    "cybersec_classifier_bot": "classification",
}


class LLMEndpoint(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    base_url: str = Field(min_length=1)
    model: str = ""
    api_format: Literal["responses", "chat_completions"] = "responses"
    processing_mode: Literal["realtime", "openrouter_batch"] = "realtime"
    api_key: str = Field(default="", repr=False)
    timeout: int = Field(default=120, gt=0)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Enter an HTTP or HTTPS provider base URL without credentials")
        if (
            parsed.port == 0
            or parsed.query
            or parsed.fragment
            or parsed.path.rstrip("/").endswith(("/responses", "/chat/completions", "/batches"))
        ):
            raise ValueError("Enter the provider base URL without an API endpoint, query, or fragment")
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_batch_model(self):
        if self.processing_mode == "openrouter_batch" and not self.model:
            raise ValueError("Batch processing requires a model ID")
        return self

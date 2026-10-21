from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


LLM_FEATURES = {
    "chat": "Chat",
    "clustering": "Story clustering",
    "summarization": "Summarization and titles",
    "ner": "Named-entity recognition",
    "sentiment": "Sentiment analysis",
    "classification": "Topic classification",
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
    enabled: bool = True
    model: str = ""
    api_format: Literal["responses", "chat_completions", "systemone", "openai_decisions"] = "responses"
    processing_mode: Literal["realtime", "openrouter_batch"] = "realtime"
    api_key: str = Field(default="", repr=False)
    timeout: int = Field(default=120, gt=0)

    @property
    def is_decisions(self) -> bool:
        return self.api_format in {"systemone", "openai_decisions"}

    @model_validator(mode="after")
    def validate_transport(self):
        if self.is_decisions and self.processing_mode != "realtime":
            raise ValueError("Decisions endpoints require realtime processing")
        if not self.is_decisions and urlparse(self.base_url).path.endswith(("/decisions", "/systemone")):
            raise ValueError("Select a Decisions API format for this endpoint")
        return self

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


type LLMAPIFormat = Literal["responses", "chat_completions", "systemone", "openai_decisions"]

LLM_API_FORMATS: dict[LLMAPIFormat, str] = {
    "responses": "Responses",
    "chat_completions": "Chat Completions",
    "systemone": "Decisions (System One / OpenRouter)",
    "openai_decisions": "Decisions (OpenAI)",
}
DECISIONS_FORMATS = {"systemone", "openai_decisions"}


class LLMAPIConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    model: str = ""
    base_url: str = ""

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        return LLMEndpoint.validate_base_url(value) if value else ""


class LLMProvider(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    base_url: str = Field(min_length=1)
    enabled: bool = True
    api_formats: dict[LLMAPIFormat, LLMAPIConfig] = Field(min_length=1)
    processing_mode: Literal["realtime", "openrouter_batch"] = "realtime"
    api_key: str = Field(default="", repr=False)
    timeout: int = Field(default=120, gt=0)

    @model_validator(mode="before")
    @classmethod
    def normalize_single_format(cls, data):
        if isinstance(data, dict):
            data = dict(data)
            api_format = data.pop("api_format", "responses")
            model = data.pop("model", "")
            data.setdefault("api_formats", {api_format: {"model": model}})
        return data

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        return LLMEndpoint.validate_base_url(value)

    @model_validator(mode="after")
    def validate_formats(self):
        for api_format in self.api_formats:
            self.for_format(api_format)
        if self.processing_mode == "openrouter_batch" and not self.supports("chat"):
            raise ValueError("Decisions endpoints require realtime processing")
        return self

    def supports(self, feature: str) -> bool:
        return any((api_format in DECISIONS_FORMATS) == (feature == "classification") for api_format in self.api_formats)

    def for_feature(self, feature: str) -> dict | None:
        for api_format in LLM_API_FORMATS:
            if api_format in self.api_formats and (api_format in DECISIONS_FORMATS) == (feature == "classification"):
                return self.for_format(api_format)
        return None

    def for_format(self, api_format: LLMAPIFormat) -> dict:
        config = self.api_formats[api_format]
        base_url = config.base_url or self.base_url
        if api_format in DECISIONS_FORMATS and not urlparse(base_url).path.endswith(("/systemone", "/decisions")):
            base_url += "/systemone" if api_format == "systemone" else "/decisions"
        return LLMEndpoint(
            name=self.name,
            base_url=base_url,
            enabled=self.enabled,
            api_format=api_format,
            model=config.model,
            processing_mode="realtime" if api_format in DECISIONS_FORMATS else self.processing_mode,
            api_key=self.api_key,
            timeout=self.timeout,
        ).model_dump()

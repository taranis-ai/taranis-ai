from typing import Annotated, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


type EmbeddingDimensions = Annotated[int, Field(ge=1, le=16000)]


class EmbeddingDimensionMismatch(ValueError):
    public_message = "Embedding output dimensions do not match the index or configured override. Check the model and rebuild the index."


LLM_FEATURES = {
    "chat": "Chat",
    "embedding": "HRAG embeddings",
    "graph_planning": "HRAG graph planning",
    "extraction": "HRAG entity and relationship extraction",
    "extraction_verification": "HRAG relationship verification",
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
    dimensions: EmbeddingDimensions | None = Field(default=None, exclude_if=lambda value: value is None)
    api_format: Literal["responses", "chat_completions", "systemone", "openai_decisions", "embeddings"] = "responses"
    processing_mode: Literal["realtime", "openrouter_batch"] = "realtime"
    api_key: str = Field(default="", repr=False)
    timeout: int = Field(default=120, gt=0)

    @property
    def is_decisions(self) -> bool:
        return self.api_format in {"systemone", "openai_decisions"}

    @model_validator(mode="after")
    def validate_transport(self):
        if self.dimensions is not None and self.api_format != "embeddings":
            raise ValueError("Dimensions apply only to embeddings")
        if (self.is_decisions or self.api_format == "embeddings") and self.processing_mode != "realtime":
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
            or parsed.path.rstrip("/").endswith(("/responses", "/chat/completions", "/batches", "/embeddings"))
        ):
            raise ValueError("Enter the provider base URL without an API endpoint, query, or fragment")
        return value.rstrip("/")


type LLMAPIFormat = Literal["responses", "chat_completions", "systemone", "openai_decisions", "embeddings"]

LLM_API_FORMATS: dict[LLMAPIFormat, str] = {
    "embeddings": "Embeddings",
    "responses": "Responses",
    "chat_completions": "Chat Completions",
    "systemone": "Decisions (System One / OpenRouter)",
    "openai_decisions": "Decisions (OpenAI)",
}
DECISIONS_FORMATS = {"systemone", "openai_decisions"}


type EndpointFailureReason = Literal[
    "model_missing",
    "request_rejected",
    "authentication_failed",
    "billing_required",
    "forbidden",
    "not_found",
    "rate_limited",
    "service_unavailable",
    "http_error",
    "timeout",
    "connection_failed",
    "tls_failed",
    "invalid_response",
    "invalid_configuration",
    "batch_failed",
    "provider_error",
    "embedding_dimensions_mismatch",
    "embedding_dimensions_unsupported",
]

ENDPOINT_CHECK_MESSAGES = {
    "model_missing": "Request rejected with no model ID configured. Enter a model ID if required by this provider, or disable this API format.",
    "request_rejected": "Request rejected. Check the model ID, API format and supported parameters.",
    "authentication_failed": "Authentication failed. Check the saved API key.",
    "billing_required": "Provider requires payment or credits. Check the provider account.",
    "forbidden": "Access denied. Check API key permissions and model access.",
    "not_found": "API path or model not found. Check the base URL, API format and model ID.",
    "rate_limited": "Provider rate limit reached. Wait and try again or check the account limits.",
    "service_unavailable": "Provider service is unavailable. Try again later.",
    "http_error": "Provider returned an HTTP error. Check the endpoint configuration.",
    "timeout": "Provider request timed out. Check service availability and the configured timeout.",
    "connection_failed": "Could not connect to the provider. Check the URL, network and service availability.",
    "tls_failed": "TLS certificate verification failed. Check the provider certificate and trusted certificate authorities.",
    "invalid_response": "Provider returned invalid or empty output for this API format. Check the model and API format.",
    "invalid_configuration": "Invalid endpoint configuration. Check the API format, model and processing mode.",
    "batch_failed": "Batch check failed. Check the model's batch support and provider batch status.",
    "provider_error": "Provider inference failed. Check the model and service availability.",
    "embedding_dimensions_mismatch": "Embedding output does not match the configured dimensions. Clear the dimension override for Automatic, or choose a supported size.",
    "embedding_dimensions_unsupported": "Embedding output exceeds the supported size of 16000 dimensions. Select a smaller output size.",
}


class EndpointFormatCheck(BaseModel):
    status: Literal["up", "down", "pending"]
    failure_reason: EndpointFailureReason | None = None
    http_status: int | None = Field(default=None, ge=400, le=599, strict=True)

    def public_message(self, api_format: LLMAPIFormat) -> str:
        message = "Check succeeded." if self.status == "up" else "Check pending."
        if self.status == "down":
            message = ENDPOINT_CHECK_MESSAGES.get(self.failure_reason or "invalid_response", ENDPOINT_CHECK_MESSAGES["invalid_response"])
        status = f" (HTTP {self.http_status})" if self.http_status else ""
        return f"{LLM_API_FORMATS[api_format]}{status}: {message}"


class EndpointCheckResult(BaseModel):
    check_id: str
    healthy: bool = Field(strict=True)
    embedding_dimensions: EmbeddingDimensions | None = None
    formats: dict[LLMAPIFormat, EndpointFormatCheck] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_overall_health(self):
        if self.formats and self.healthy != all(check.status == "up" for check in self.formats.values()):
            raise ValueError("Overall endpoint health must match the API format results")
        return self


class LLMAPIConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    model: str = ""
    base_url: str = ""
    dimensions: EmbeddingDimensions | None = Field(default=None, exclude_if=lambda value: value is None)

    @field_validator("dimensions", mode="before")
    @classmethod
    def normalize_dimensions(cls, value):
        return None if value == "" else value

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

    @staticmethod
    def feature_formats(feature: str) -> tuple[str, ...]:
        if feature == "embedding":
            return ("embeddings",)
        if feature in {"classification", "sentiment", "extraction_verification"}:
            return ("systemone", "openai_decisions")
        return ("responses", "chat_completions")

    def supports(self, feature: str) -> bool:
        return bool(set(self.api_formats) & set(self.feature_formats(feature)))

    def for_feature(self, feature: str) -> dict | None:
        for api_format in LLM_API_FORMATS:
            if api_format in self.api_formats and api_format in self.feature_formats(feature):
                return self.for_format(api_format)
        return None

    def for_format(self, api_format: LLMAPIFormat) -> dict:
        config = self.api_formats[api_format]
        base_url = config.base_url or self.base_url
        if not config.base_url and api_format in DECISIONS_FORMATS and not urlparse(base_url).path.endswith(("/systemone", "/decisions")):
            base_url += "/systemone" if api_format == "systemone" else "/decisions"
        return LLMEndpoint(
            name=self.name,
            base_url=base_url,
            enabled=self.enabled,
            api_format=api_format,
            model=config.model,
            dimensions=config.dimensions,
            processing_mode="realtime" if api_format in DECISIONS_FORMATS or api_format == "embeddings" else self.processing_mode,
            api_key=self.api_key,
            timeout=self.timeout,
        ).model_dump()

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ORCAROUTER_PROVIDER_ID = "orcarouter"
ORCAROUTER_DEFAULT_BASE_URL = "https://api.orcarouter.ai/v1"
ORCAROUTER_DEFAULT_MODEL = "orcarouter/auto"
ORCAROUTER_CYBER_URL = "https://www.orcarouter.ai/cyber"
ORCAROUTER_TIER_URL = "https://www.orcarouter.ai/models?tier=cyber"
ORCAROUTER_KEYS_URL = "https://www.orcarouter.ai/console"

# First-class provider entries for the LLM endpoint form. Existing saved
# endpoints without a provider keep the generic OpenAI-compatible behaviour.
LLM_PROVIDERS = {
    "openai_compatible": {
        "name": "OpenAI-compatible",
        "base_url": "",
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
    },
    "orcarouter": {
        "name": "OrcaRouter Cyber Inference",
        "base_url": ORCAROUTER_DEFAULT_BASE_URL,
        "default_model": ORCAROUTER_DEFAULT_MODEL,
        "cyber_url": ORCAROUTER_CYBER_URL,
        "tier_url": ORCAROUTER_TIER_URL,
        "keys_url": ORCAROUTER_KEYS_URL,
    },
}

# Small, verified outage catalogue. Live discovery is authoritative whenever it
# succeeds; these records keep a fresh installation usable during an outage.
# Capabilities mirror the public catalogue verified on 2026-10-24.
ORCAROUTER_FALLBACK_MODELS: tuple[dict, ...] = (
    {
        "id": "orcarouter/auto",
        "name": "OrcaRouter Auto",
        "supported_endpoint_types": ["openai", "openai-response", "anthropic", "gemini"],
        "input_modalities": ["text"],
        "reasoning_efforts": [],
    },
    {
        "id": "orcarouter/fusion",
        "name": "OrcaRouter Fusion",
        "supported_endpoint_types": ["openai", "openai-response", "anthropic", "gemini"],
        "input_modalities": ["text"],
        "context_window": 1000000,
        "reasoning_efforts": [],
    },
    {
        "id": "orca/orcacyber-ultra-1.0",
        "name": "OrcaCyber Ultra 1.0",
        "supported_endpoint_types": ["openai"],
        "input_modalities": ["text"],
        "context_window": 1048576,
        "reasoning_efforts": [],
    },
    {
        "id": "orca/orcacyber-zero-1.5",
        "name": "OrcaCyber Zero 1.5",
        "supported_endpoint_types": ["openai"],
        "input_modalities": ["text"],
        "context_window": 1000000,
        "reasoning_efforts": [],
    },
    {
        "id": "openai/gpt-5.5",
        "name": "OpenAI: GPT-5.5",
        "supported_endpoint_types": ["openai", "openai-response"],
        "input_modalities": ["text", "image", "file"],
        "reasoning_efforts": ["low", "medium", "high", "xhigh"],
    },
    {
        "id": "anthropic/claude-opus-4.8",
        "name": "Anthropic: Claude Opus 4.8",
        "supported_endpoint_types": ["openai", "anthropic", "openai-response"],
        "input_modalities": ["text", "image", "file"],
        "context_window": 1000000,
        "reasoning_efforts": [],
    },
    {
        "id": "google/gemini-3.5-flash",
        "name": "Gemini 3.5 Flash",
        "supported_endpoint_types": ["openai", "gemini"],
        "input_modalities": ["text", "image", "video", "file", "audio"],
        "context_window": 1048576,
        "reasoning_efforts": [],
    },
    {
        "id": "deepseek/deepseek-v4-pro",
        "name": "DeepSeek: DeepSeek V4 Pro",
        "supported_endpoint_types": ["openai", "openai-response"],
        "input_modalities": ["text"],
        "context_window": 1048576,
        "reasoning_efforts": [],
    },
)

_CHAT_ENDPOINT_TYPES = {"openai", "openai-response", "anthropic", "gemini"}
_RESPONSE_ENDPOINT_TYPES = {"openai-response"}
_CHAT_COMPLETION_ENDPOINT_TYPES = {"openai"}
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}

CAPABILITY_ENDPOINT_TYPES = {
    "chat": _CHAT_ENDPOINT_TYPES,
    "embedding": {"embeddings"},
    "image": {"image-generation"},
    "video": {"openai-video"},
    "rerank": {"jina-rerank"},
}


def _endpoint_types(model: dict) -> set[str]:
    raw = model.get("supported_endpoint_types") or []
    return {str(item).casefold() for item in raw if isinstance(item, str)}


def _input_modalities(model: dict) -> set[str]:
    architecture = model.get("architecture")
    raw = architecture.get("input_modalities") if isinstance(architecture, dict) else model.get("input_modalities")
    if not isinstance(raw, list):
        return set()
    return {str(item).casefold() for item in raw if isinstance(item, str)}


def _output_modalities(model: dict) -> set[str]:
    architecture = model.get("architecture")
    raw = architecture.get("output_modalities") if isinstance(architecture, dict) else model.get("output_modalities")
    if not isinstance(raw, list):
        return set()
    return {str(item).casefold() for item in raw if isinstance(item, str)}


def catalog_model_matches(
    model: dict,
    capability: str,
    *,
    api_format: str | None = None,
    required_input_modalities: tuple[str, ...] = (),
) -> bool:
    """Fail-closed capability filter for a provider model catalogue record."""
    if not isinstance(model, dict) or not isinstance(model.get("id"), str) or not model["id"]:
        return False
    endpoint_types = _endpoint_types(model)
    required_types = CAPABILITY_ENDPOINT_TYPES.get(capability)
    if not required_types or not (endpoint_types & required_types):
        return False
    if capability == "chat":
        if api_format == "responses" and not (endpoint_types & _RESPONSE_ENDPOINT_TYPES):
            return False
        if api_format == "chat_completions" and not (endpoint_types & _CHAT_COMPLETION_ENDPOINT_TYPES):
            return False
        output_modalities = _output_modalities(model)
        if output_modalities and "text" not in output_modalities:
            return False
    required = {item.casefold() for item in required_input_modalities}
    return not required or required.issubset(_input_modalities(model))


def filter_catalog_models(
    models: list[dict],
    capability: str,
    *,
    api_format: str | None = None,
    required_input_modalities: tuple[str, ...] = (),
    limit: int = 1000,
) -> list[dict]:
    selected = [
        model
        for model in models
        if catalog_model_matches(
            model,
            capability,
            api_format=api_format,
            required_input_modalities=required_input_modalities,
        )
    ]
    return selected[:limit]


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
    provider: Literal["openai_compatible", "openrouter", "orcarouter"] = "openai_compatible"
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
            if data.get("provider") == ORCAROUTER_PROVIDER_ID and not data.get("base_url"):
                data["base_url"] = ORCAROUTER_DEFAULT_BASE_URL
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
        if self.provider == ORCAROUTER_PROVIDER_ID:
            if self.processing_mode != "realtime":
                raise ValueError("OrcaRouter endpoints require realtime processing")
            if any(api_format in DECISIONS_FORMATS for api_format in self.api_formats):
                raise ValueError("OrcaRouter does not provide a Decisions endpoint")
            parsed = urlparse(self.base_url)
            if parsed.scheme != "https" and parsed.hostname not in _LOOPBACK_HOSTS:
                raise ValueError("OrcaRouter endpoints require HTTPS except for loopback development")
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
        if not config.base_url and api_format in DECISIONS_FORMATS and not urlparse(base_url).path.endswith(("/systemone", "/decisions")):
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

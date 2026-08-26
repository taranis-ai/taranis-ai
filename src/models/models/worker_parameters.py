"""Authoritative worker parameter contracts and boundary serialization."""

import json
from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    SecretStr,
    TypeAdapter,
    field_validator,
    model_validator,
)

from models.types import WORKER_CATEGORY, WORKER_TYPES, TLPLevel


def _empty_to_none(value: Any) -> Any:
    return None if value == "" else value


def _json_object(value: Any) -> Any:
    if isinstance(value, str):
        if not value.strip():
            return {}
        return json.loads(value)
    return value


def _string_list(value: Any) -> Any:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


OptionalPositiveInt = Annotated[Annotated[int, Field(gt=0)] | None, BeforeValidator(_empty_to_none)]
JsonObject = Annotated[dict[str, Any], BeforeValidator(_json_object)]
StringList = Annotated[list[str], BeforeValidator(_string_list)]
Cron = Annotated[
    str,
    Field(
        pattern=r"^(?:\s*$|\s*(\S+\s+){4}\S+\s*)$",
        json_schema_extra={"widget": "cron"},
    ),
]


class WorkerParameters(BaseModel):
    """Base for configured worker parameters.

    Validated native values are preserved across persistence, APIs, and worker execution.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class WebCollectorParameters(WorkerParameters):
    USER_AGENT: str = Field("", title="User agent", description="HTTP User-Agent header sent by the collector.")
    PROXY_SERVER: str = Field("", title="Proxy server", description="Optional proxy URL used for requests.")
    USE_GLOBAL_PROXY: bool = Field(False, title="Use global proxy", description="Use the globally configured proxy.")
    ADDITIONAL_HEADERS: JsonObject = Field(
        default_factory=dict,
        title="Additional headers",
        description="Additional HTTP headers as a JSON object.",
        json_schema_extra={"widget": "textarea"},
    )
    TLP_LEVEL: TLPLevel = Field(TLPLevel.CLEAR, title="TLP level", description="Traffic Light Protocol level assigned to collected items.")
    REFRESH_INTERVAL: Cron = Field("", title="Refresh interval", description="Five-field cron schedule for collection.")
    DIGEST_SPLITTING: bool = Field(False, title="Digest splitting", description="Split digest-style pages into individual items.")
    DIGEST_SPLITTING_LIMIT: int = Field(30, gt=0, title="Digest splitting limit", description="Maximum number of digest entries to split.")
    BROWSER_MODE: bool = Field(False, title="Browser mode", description="Render the page in a browser before extraction.")


class RSSCollectorParameters(WebCollectorParameters):
    FEED_URL: str = Field(min_length=1, title="Feed URL", description="URL of the RSS or Atom feed.")
    CONTENT_LOCATION: str = Field("", title="Content location", description="Optional selector identifying the content location.")
    USE_FEED_CONTENT: bool = Field(
        False, title="Use feed content", description="Use content embedded in the feed instead of fetching the linked page."
    )
    XPATH: str = Field("", title="XPath", description="Optional XPath expression selecting article content.")


class SimpleWebCollectorParameters(WebCollectorParameters):
    WEB_URL: str = Field(min_length=1, title="Web URL", description="URL of the web page to collect.")
    XPATH: str = Field("", title="XPath", description="Optional XPath expression selecting article content.")


class PPNCollectorParameters(WorkerParameters):
    PATH: str = Field(min_length=1, title="Path", description="Path to the PPN dataset.")
    TLP_LEVEL: TLPLevel = Field(TLPLevel.CLEAR, title="TLP level", description="Traffic Light Protocol level assigned to collected items.")
    REFRESH_INTERVAL: Cron = Field("", title="Refresh interval", description="Five-field cron schedule for collection.")
    DIGEST_SPLITTING: bool = Field(False, title="Digest splitting", description="Split digest-style records into individual items.")


class ManualCollectorParameters(WorkerParameters):
    TLP_LEVEL: TLPLevel = Field(
        TLPLevel.CLEAR, title="TLP level", description="Traffic Light Protocol level assigned to manually created items."
    )


class RTCollectorParameters(WorkerParameters):
    BASE_URL: str = Field(min_length=1, title="Base URL", description="Request Tracker base URL.")
    USER_AGENT: str = Field("", title="User agent", description="HTTP User-Agent header sent by the collector.")
    PROXY_SERVER: str = Field("", title="Proxy server", description="Optional proxy URL used for requests.")
    USE_GLOBAL_PROXY: bool = Field(False, title="Use global proxy", description="Use the globally configured proxy.")
    ADDITIONAL_HEADERS: JsonObject = Field(
        default_factory=dict,
        title="Additional headers",
        description="Additional HTTP headers as a JSON object.",
        json_schema_extra={"widget": "textarea"},
    )
    RT_TOKEN: SecretStr = Field(min_length=1, title="RT token", description="Authentication token for Request Tracker.")
    SEARCH_QUERY: str = Field("", title="Search query", description="Request Tracker search query.")
    FIELDS_TO_INCLUDE: StringList = Field(
        default_factory=list, title="Fields to include", description="Comma-separated Request Tracker fields to include."
    )
    TLP_LEVEL: TLPLevel = Field(TLPLevel.CLEAR, title="TLP level", description="Traffic Light Protocol level assigned to collected items.")
    REFRESH_INTERVAL: Cron = Field("", title="Refresh interval", description="Five-field cron schedule for collection.")


class MISPBaseParameters(WorkerParameters):
    URL: str = Field(min_length=1, title="URL", description="MISP server URL.")
    API_KEY: SecretStr = Field(min_length=1, title="API key", description="MISP API key.")
    ORGANISATION_ID: str = Field(min_length=1, title="Organisation ID", description="MISP organisation identifier.")
    SSL_CHECK: bool = Field(False, title="SSL check", description="Verify the MISP server TLS certificate.")
    REQUEST_TIMEOUT: OptionalPositiveInt = Field(None, title="Request timeout", description="Request timeout in seconds.")
    USER_AGENT: str = Field("", title="User agent", description="HTTP User-Agent header sent to MISP.")
    PROXY_SERVER: str = Field("", title="Proxy server", description="Optional proxy URL used for requests.")
    USE_GLOBAL_PROXY: bool = Field(False, title="Use global proxy", description="Use the globally configured proxy.")
    ADDITIONAL_HEADERS: JsonObject = Field(
        default_factory=dict,
        title="Additional headers",
        description="Additional HTTP headers as a JSON object.",
        json_schema_extra={"widget": "textarea"},
    )
    REFRESH_INTERVAL: Cron = Field("", title="Refresh interval", description="Five-field cron schedule.")
    SHARING_GROUP_ID: OptionalPositiveInt = Field(None, title="Sharing group ID", description="Optional MISP sharing-group identifier.")


class MISPCollectorParameters(MISPBaseParameters):
    DAYS_WITHOUT_CHANGE: OptionalPositiveInt = Field(
        None, title="Days without change", description="Ignore events unchanged for more than this many days."
    )


class MISPConnectorParameters(MISPBaseParameters):
    REQUEST_TIMEOUT: OptionalPositiveInt = Field(5, title="Request timeout", description="Request timeout in seconds.")
    DISTRIBUTION: Literal["0", "1", "2", "3", "4"] | None = Field(None, title="Distribution", description="MISP distribution level.")

    @field_validator("DISTRIBUTION", mode="before")
    @classmethod
    def empty_distribution(cls, value: Any) -> Any:
        return None if value == "" else value


class BotParameters(WorkerParameters):
    ITEM_FILTER: str = Field("", title="Item filter", description="Filter selecting items processed by the bot.")
    RUN_AFTER_COLLECTOR: bool = Field(False, title="Run after collector", description="Run automatically after collection.")
    RUN_AFTER_BOTS: StringList = Field(default_factory=list, title="Run after bots", description="Bot identifiers that must finish first.")
    REFRESH_INTERVAL: Cron = Field("", title="Refresh interval", description="Five-field cron schedule for periodic execution.")


class AnalystBotParameters(BotParameters):
    REGULAR_EXPRESSION: str = Field("", title="Regular expression", description="Regular expression used to extract an attribute.")
    ATTRIBUTE_NAME: str = Field("", title="Attribute name", description="Name assigned to the extracted attribute.")


class GroupingBotParameters(BotParameters):
    REGULAR_EXPRESSION: str = Field("", title="Regular expression", description="Regular expression used to group related items.")


class LLMParameters(BotParameters):
    REQUESTS_TIMEOUT: OptionalPositiveInt = Field(None, title="Requests timeout", description="LLM request timeout in seconds.")
    BOT_API_KEY: SecretStr = Field(SecretStr(""), title="Bot API key", description="Optional API key for the bot service.")


class NLPBotParameters(LLMParameters):
    BOT_ENDPOINT: str = Field("http://llm-bot:8000/ner", title="Bot endpoint", description="Named-entity recognition service endpoint.")


class IOCBotParameters(BotParameters):
    pass


class IntelOwlBotParameters(BotParameters):
    INTEL_OWL_URL: str = Field(min_length=1, title="IntelOwl URL", description="IntelOwl service URL.")
    INTEL_OWL_API_KEY: SecretStr = Field(min_length=1, title="IntelOwl API key", description="IntelOwl API key.")
    INTEL_OWL_TLS_VERIFY: bool = Field(True, title="Verify TLS", description="Verify the IntelOwl TLS certificate.")
    INTEL_OWL_TLP: Literal["CLEAR", "GREEN", "AMBER", "RED"] = Field(
        "CLEAR", title="IntelOwl TLP", description="TLP level submitted to IntelOwl."
    )
    INTEL_OWL_POLL_TIMEOUT_SECONDS: int = Field(1800, gt=0, title="Poll timeout", description="Maximum IntelOwl polling duration in seconds.")


class TaggingBotParameters(BotParameters):
    REGULAR_EXPRESSION: str = Field(
        min_length=1,
        title="Regular expression",
        description="Regular expression used to extract tags from news-item content.",
    )


class StoryBotParameters(LLMParameters):
    ITEM_FILTER: str = Field("range=week", title="Item filter", description="Filter selecting items processed by the bot.")
    BOT_ENDPOINT: str = Field("http://llm-bot:8000/cluster", title="Bot endpoint", description="Story clustering service endpoint.")


class SummaryBotParameters(LLMParameters):
    SUMMARY_ENDPOINT: str = Field(
        "http://llm-bot:8000/summarize", title="Summary endpoint", description="Summary generation service endpoint."
    )
    TITLE_ENDPOINT: str = Field("http://llm-bot:8000/title", title="Title endpoint", description="Title generation service endpoint.")


class WordlistBotParameters(BotParameters):
    TAGGING_WORDLISTS: StringList = Field(
        default_factory=list,
        title="Tagging word lists",
        description="Word-list identifiers used for tagging.",
        json_schema_extra={"widget": "word-list-table"},
    )
    IGNORECASE: bool = Field(True, title="Ignore case", description="Match word-list entries without case sensitivity.")
    OVERRIDE_EXISTING_TAGS: bool = Field(
        True,
        title="Override existing tags",
        description="Replace the category of tags that already exist on an item.",
    )


class SentimentAnalysisBotParameters(LLMParameters):
    BOT_ENDPOINT: str = Field("http://llm-bot:8000/sentiment", title="Bot endpoint", description="Sentiment analysis service endpoint.")
    RUN_AFTER_COLLECTOR: bool = Field(True, title="Run after collector", description="Run automatically after collection.")


class CybersecClassifierBotParameters(LLMParameters):
    BOT_ENDPOINT: str = Field(
        "http://llm-bot:8000/cybersec-classification", title="Bot endpoint", description="Cybersecurity classifier service endpoint."
    )
    CLASSIFICATION_THRESHOLD: float = Field(
        0.65, ge=0, le=1, title="Classification threshold", description="Minimum score classified as cybersecurity-related."
    )


class TemplatePresenterParameters(WorkerParameters):
    TEMPLATE_PATH: str = Field(
        min_length=1, title="Template", description="Template used to render the product.", json_schema_extra={"widget": "template-selector"}
    )


class PandocPresenterParameters(TemplatePresenterParameters):
    CONVERT_FROM: Literal["html", "md"] = Field(title="Convert from", description="Input format passed to Pandoc.")
    CONVERT_TO: Literal["docx", "odt"] = Field(title="Convert to", description="Output format produced by Pandoc.")


class PDFPresenterParameters(TemplatePresenterParameters):
    pass


class HTMLPresenterParameters(TemplatePresenterParameters):
    pass


class TextPresenterParameters(TemplatePresenterParameters):
    pass


class JSONPresenterParameters(TemplatePresenterParameters):
    pass


class STIXPresenterParameters(WorkerParameters):
    pass


class TaranisPublisherParameters(WorkerParameters):
    pass


class FTPPublisherParameters(WorkerParameters):
    FTP_URL: str = Field(min_length=1, title="FTP URL", description="Destination FTP URL.")


class SFTPPublisherParameters(WorkerParameters):
    SFTP_URL: str = Field(min_length=1, title="SFTP URL", description="Destination SFTP URL.")
    PRIVATE_KEY: SecretStr = Field(
        SecretStr(""), title="Private key", description="Optional SSH private key.", json_schema_extra={"widget": "textarea"}
    )


class S3PublisherParameters(WorkerParameters):
    S3_ENDPOINT: str = Field(min_length=1, title="S3 endpoint", description="S3-compatible service endpoint.")
    S3_ACCESS_KEY: SecretStr = Field(min_length=1, title="S3 access key", description="S3 access key.")
    S3_SECRET_KEY: SecretStr = Field(min_length=1, title="S3 secret key", description="S3 secret key.")
    S3_BUCKET_NAME: str = Field(min_length=1, title="S3 bucket name", description="Destination bucket name.")
    S3_SESSION_TOKEN: SecretStr = Field(SecretStr(""), title="S3 session token", description="Optional temporary session token.")
    S3_REGION: str = Field("", title="S3 region", description="Optional S3 region.")
    S3_SECURE: bool = Field(True, title="Secure connection", description="Use TLS for the S3 connection.")
    S3_CERT_CHECK: bool = Field(True, title="Certificate check", description="Verify the S3 TLS certificate.")


class EmailPublisherParameters(WorkerParameters):
    SMTP_SERVER_ADDRESS: str = Field(min_length=1, title="SMTP server address", description="SMTP server hostname or address.")
    SMTP_SERVER_PORT: int = Field(25, gt=0, le=65535, title="SMTP server port", description="SMTP server port.")
    SERVER_TLS: bool = Field(False, title="Server TLS", description="Use TLS for SMTP.")
    EMAIL_USERNAME: str = Field("", title="Email username", description="Optional SMTP username.")
    EMAIL_PASSWORD: SecretStr = Field(SecretStr(""), title="Email password", description="Optional SMTP password.")
    EMAIL_SENDER: str = Field(min_length=1, title="Email sender", description="Sender email address.")
    EMAIL_RECIPIENT: str = Field(min_length=1, title="Email recipient", description="Recipient email address.")
    EMAIL_SUBJECT: str = Field("", title="Email subject", description="Optional subject of the published email.")


class WordpressPublisherParameters(WorkerParameters):
    WP_URL: str = Field(min_length=1, title="WordPress URL", description="WordPress site URL.")
    WP_USER: str = Field(min_length=1, title="WordPress user", description="WordPress username.")
    WP_PYTHON_APP_SECRET: SecretStr = Field(min_length=1, title="WordPress application secret", description="WordPress application password.")


class MISPPublisherParameters(WorkerParameters):
    MISP_URL: str = Field(min_length=1, title="MISP URL", description="MISP server URL.")
    MISP_API_KEY: SecretStr = Field(min_length=1, title="MISP API key", description="MISP API key.")


class TaxiiPublisherParameters(WorkerParameters):
    TAXII_DISCOVERY_URL: str = Field("", title="Discovery URL", description="TAXII discovery endpoint; required when API root URL is absent.")
    TAXII_API_ROOT_URL: str = Field("", title="API root URL", description="TAXII API root URL; discovered when omitted.")
    TAXII_COLLECTION_ID: str = Field(min_length=1, title="Collection ID", description="Target TAXII collection identifier.")
    AUTH_TYPE: Literal["basic", "bearer"] = Field(
        "basic", title="Authentication type", description="Authentication method used by the TAXII server."
    )
    USERNAME: str = Field("", title="Username", description="Username for basic authentication.")
    PASSWORD: SecretStr = Field(SecretStr(""), title="Password", description="Password for basic authentication.")
    API_TOKEN: SecretStr = Field(SecretStr(""), title="API token", description="Bearer token for bearer authentication.")
    SSL_VERIFY: bool = Field(True, title="Verify SSL", description="Verify the TAXII TLS certificate.")
    PROXY_SERVER: str = Field("", title="Proxy server", description="Optional proxy URL used for requests.")

    @model_validator(mode="after")
    def validate_endpoint_and_auth(self) -> "TaxiiPublisherParameters":
        if not self.TAXII_DISCOVERY_URL and not self.TAXII_API_ROOT_URL:
            raise ValueError("TAXII_DISCOVERY_URL or TAXII_API_ROOT_URL is required")
        if self.AUTH_TYPE == "basic" and (not self.USERNAME or not self.PASSWORD.get_secret_value()):
            raise ValueError("USERNAME and PASSWORD are required for basic authentication")
        if self.AUTH_TYPE == "bearer" and not self.API_TOKEN.get_secret_value():
            raise ValueError("API_TOKEN is required for bearer authentication")
        return self


class KafkaPublisherParameters(WorkerParameters):
    KAFKA_TOPIC: str = Field(min_length=1, title="Kafka topic", description="Destination Kafka topic.")
    KAFKA_BOOTSTRAP_SERVERS: str = Field(min_length=1, title="Bootstrap servers", description="Comma-separated Kafka bootstrap servers.")
    KAFKA_SECURITY_PROTOCOL: Literal["PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"] = Field(
        "PLAINTEXT", title="Security protocol", description="Kafka transport security protocol."
    )
    KAFKA_SASL_MECHANISM: str = Field("", title="SASL mechanism", description="SASL mechanism when SASL is enabled.")
    KAFKA_SASL_USERNAME: str = Field("", title="SASL username", description="SASL username.")
    KAFKA_SASL_PASSWORD: SecretStr = Field(SecretStr(""), title="SASL password", description="SASL password.")
    KAFKA_ACKS: Literal["0", "1", "all"] = Field("all", title="Acknowledgements", description="Kafka producer acknowledgement policy.")
    KAFKA_RETRIES: int = Field(3, ge=0, title="Retries", description="Number of producer retries.")
    KAFKA_SEND_TIMEOUT: int = Field(30, gt=0, title="Send timeout", description="Producer flush timeout in seconds.")

    @model_validator(mode="after")
    def validate_sasl(self) -> "KafkaPublisherParameters":
        if self.KAFKA_SECURITY_PROTOCOL.startswith("SASL") and (
            missing := [
                name
                for name, value in (
                    ("KAFKA_SASL_MECHANISM", self.KAFKA_SASL_MECHANISM),
                    ("KAFKA_SASL_USERNAME", self.KAFKA_SASL_USERNAME),
                    (
                        "KAFKA_SASL_PASSWORD",
                        self.KAFKA_SASL_PASSWORD.get_secret_value(),
                    ),
                )
                if not value
            ]
        ):
            raise ValueError(f"SASL parameters are required: {', '.join(missing)}")
        return self


@dataclass(frozen=True)
class WorkerDefinition:
    type: WORKER_TYPES
    category: WORKER_CATEGORY
    name: str
    description: str
    parameter_model: type[WorkerParameters]


def _definition(
    worker_type: WORKER_TYPES,
    name: str,
    description: str,
    parameter_model: type[WorkerParameters],
) -> WorkerDefinition:
    category = WORKER_CATEGORY(worker_type.value.rsplit("_", 1)[1])
    return WorkerDefinition(worker_type, category, name, description, parameter_model)


_DEFINITIONS = (
    _definition(WORKER_TYPES.RSS_COLLECTOR, "RSS Collector", "Collector for gathering data from RSS feeds", RSSCollectorParameters),
    _definition(
        WORKER_TYPES.SIMPLE_WEB_COLLECTOR, "Simple Web Collector", "Collector for gathering data from a website", SimpleWebCollectorParameters
    ),
    _definition(WORKER_TYPES.PPN_COLLECTOR, "PPN Collector", "Collector for gathering news from the PPN dataset", PPNCollectorParameters),
    _definition(WORKER_TYPES.MANUAL_COLLECTOR, "Manual", "Manual source for creating news items via UI", ManualCollectorParameters),
    _definition(WORKER_TYPES.RT_COLLECTOR, "RT Collector", "Collector for gathering data from Request Tracker", RTCollectorParameters),
    _definition(WORKER_TYPES.MISP_COLLECTOR, "MISP Collector", "Collector for MISP", MISPCollectorParameters),
    _definition(WORKER_TYPES.ANALYST_BOT, "Analyst Bot", "Bot for news item analysis", AnalystBotParameters),
    _definition(WORKER_TYPES.GROUPING_BOT, "Grouping Bot", "Bot for grouping news items into stories", GroupingBotParameters),
    _definition(WORKER_TYPES.NLP_BOT, "NLP Bot", "Bot for natural-language processing", NLPBotParameters),
    _definition(WORKER_TYPES.IOC_BOT, "IOC Bot", "Bot for extracting indicators of compromise", IOCBotParameters),
    _definition(WORKER_TYPES.INTEL_OWL_BOT, "IntelOwl Bot", "Bot for submitting observables to IntelOwl", IntelOwlBotParameters),
    _definition(WORKER_TYPES.TAGGING_BOT, "Tagging Bot", "Bot for tagging news items", TaggingBotParameters),
    _definition(WORKER_TYPES.STORY_BOT, "Story Clustering Bot", "Bot for story clustering", StoryBotParameters),
    _definition(
        WORKER_TYPES.SUMMARY_BOT, "Summary generation Bot", "Bot for summarizing stories and generating titles", SummaryBotParameters
    ),
    _definition(WORKER_TYPES.WORDLIST_BOT, "Wordlist Bot", "Bot for tagging news items by word list", WordlistBotParameters),
    _definition(WORKER_TYPES.SENTIMENT_ANALYSIS_BOT, "Sentiment Analysis Bot", "Bot for analyzing sentiment", SentimentAnalysisBotParameters),
    _definition(
        WORKER_TYPES.CYBERSEC_CLASSIFIER_BOT,
        "Cybersecurity classification bot",
        "Bot for classifying cybersecurity content",
        CybersecClassifierBotParameters,
    ),
    _definition(
        WORKER_TYPES.PANDOC_PRESENTER, "PANDOC Presenter", "Presenter for generating ODT and DOCX documents", PandocPresenterParameters
    ),
    _definition(WORKER_TYPES.PDF_PRESENTER, "PDF Presenter", "Presenter for generating PDF documents", PDFPresenterParameters),
    _definition(WORKER_TYPES.HTML_PRESENTER, "HTML Presenter", "Presenter for generating HTML documents", HTMLPresenterParameters),
    _definition(WORKER_TYPES.TEXT_PRESENTER, "TEXT Presenter", "Presenter for generating text documents", TextPresenterParameters),
    _definition(WORKER_TYPES.JSON_PRESENTER, "JSON Presenter", "Presenter for generating JSON documents", JSONPresenterParameters),
    _definition(WORKER_TYPES.STIX_PRESENTER, "STIXv2.1 Presenter", "Presenter for generating STIX reports", STIXPresenterParameters),
    _definition(
        WORKER_TYPES.TARANIS_PUBLISHER, "Taranis Publisher", "Publisher for making products available in Taranis", TaranisPublisherParameters
    ),
    _definition(WORKER_TYPES.FTP_PUBLISHER, "FTP Publisher", "Publisher for an FTP server", FTPPublisherParameters),
    _definition(WORKER_TYPES.SFTP_PUBLISHER, "SFTP Publisher", "Publisher for an SFTP server", SFTPPublisherParameters),
    _definition(WORKER_TYPES.S3_PUBLISHER, "S3 Publisher", "Publisher for S3-compatible storage", S3PublisherParameters),
    _definition(WORKER_TYPES.EMAIL_PUBLISHER, "EMAIL Publisher", "Publisher for email", EmailPublisherParameters),
    _definition(WORKER_TYPES.WORDPRESS_PUBLISHER, "WordPress Publisher", "Publisher for WordPress", WordpressPublisherParameters),
    _definition(WORKER_TYPES.MISP_PUBLISHER, "MISP Publisher", "Publisher for MISP", MISPPublisherParameters),
    _definition(WORKER_TYPES.TAXII_PUBLISHER, "TAXII Publisher", "Publisher for a TAXII 2.1 collection", TaxiiPublisherParameters),
    _definition(WORKER_TYPES.KAFKA_PUBLISHER, "KAFKA Publisher", "Publisher for a Kafka topic", KafkaPublisherParameters),
    _definition(WORKER_TYPES.MISP_CONNECTOR, "MISP Connector", "Connector for MISP", MISPConnectorParameters),
)

WORKER_DEFINITIONS: dict[WORKER_TYPES, WorkerDefinition] = {definition.type: definition for definition in _DEFINITIONS}
if len(WORKER_DEFINITIONS) != len(_DEFINITIONS) or set(WORKER_DEFINITIONS) != set(WORKER_TYPES):
    raise RuntimeError("Every worker type must have exactly one worker definition")


def get_worker_definition(worker_type: WORKER_TYPES | str) -> WorkerDefinition:
    return WORKER_DEFINITIONS[WORKER_TYPES(worker_type)]


def parameter_schema(worker_type: WORKER_TYPES | str) -> dict[str, Any]:
    return get_worker_definition(worker_type).parameter_model.model_json_schema(mode="validation", by_alias=True)


def secret_parameter_names(worker_type: WORKER_TYPES | str) -> frozenset[str]:
    model = get_worker_definition(worker_type).parameter_model
    return frozenset(
        name for name, field in model.model_fields.items() if field.annotation is SecretStr or "SecretStr" in str(field.annotation)
    )


def _plain_value(value: Any) -> Any:
    return value.get_secret_value() if isinstance(value, SecretStr) else value


def normalize_parameter_values(
    worker_type: WORKER_TYPES | str,
    values: dict[str, Any],
    *,
    complete: bool = True,
) -> dict[str, Any]:
    """Validate configured values and return submitted keys with native values."""
    model = get_worker_definition(worker_type).parameter_model
    if complete:
        validated = model.model_validate(values)
        native = validated.model_dump(mode="python")
        return {name: _plain_value(native[name]) for name in values if native[name] is not None}

    if unknown := set(values) - set(model.model_fields):
        raise ValueError(f"Unknown parameters: {', '.join(sorted(unknown))}")
    normalized: dict[str, Any] = {}
    for name, value in values.items():
        field = model.model_fields[name]
        native = TypeAdapter(field.rebuild_annotation()).validate_python(value)
        if native is not None:
            normalized[name] = _plain_value(native)
    return normalized


def effective_parameter_values(worker_type: WORKER_TYPES | str, values: dict[str, Any]) -> dict[str, Any]:
    """Validate configured values and expand defaults for worker execution."""
    validated = get_worker_definition(worker_type).parameter_model.model_validate(values)
    return {name: _plain_value(value) for name, value in validated.model_dump(mode="python").items()}


SECRET_MASK = "********"


def configured_parameter_values(worker_type: WORKER_TYPES | str, values: dict[str, Any]) -> dict[str, Any]:
    """Return configured values with secrets replaced by a stable marker."""
    secrets = secret_parameter_names(worker_type)
    return {name: SECRET_MASK if name in secrets and value else value for name, value in values.items()}

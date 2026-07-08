from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from models.base import TaranisBaseModel


CanonicalIOCType = Literal["cve", "email", "ip", "domain", "url", "hash"]

IOC_TYPE_ALIASES: dict[str, CanonicalIOCType] = {
    "cve": "cve",
    "cves": "cve",
    "email": "email",
    "email_addresses": "email",
    "ip": "ip",
    "ipv4s": "ip",
    "ipv4_cidrs": "ip",
    "ipv6s": "ip",
    "domain": "domain",
    "domains": "domain",
    "url": "url",
    "urls": "url",
    "hash": "hash",
    "md5s": "hash",
    "sha1s": "hash",
    "sha256s": "hash",
    "sha512s": "hash",
}

IOC_FINDER_TYPES = [
    "cves",
    "email_addresses",
    "ipv4s",
    "ipv4_cidrs",
    "ipv6s",
    "domains",
    "urls",
    "md5s",
    "sha1s",
    "sha256s",
    "sha512s",
]


def normalize_ioc_type(raw_type: str | None) -> CanonicalIOCType | None:
    return IOC_TYPE_ALIASES.get(str(raw_type or "").strip().lower())


def normalize_ioc_value(value: str, ioc_type: CanonicalIOCType) -> str:
    normalized = str(value or "").strip().strip(".,;:()[]{}<>\"'")
    return normalized.upper() if ioc_type == "cve" else normalized.lower()


class CTIEnrichment(TaranisBaseModel):
    ioc_type: CanonicalIOCType
    value: str
    status: str | None = None
    analyzers: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    submitted_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime | None = None


class CTIItem(TaranisBaseModel):
    ioc_type: CanonicalIOCType
    value: str
    news_item_ids: list[str] = Field(default_factory=list)
    enrichment: CTIEnrichment | None = None


class CTIResponse(TaranisBaseModel):
    item_type: Literal["news_item", "story", "report", "asset"]
    item_id: str
    iocs: list[CTIItem] = Field(default_factory=list)

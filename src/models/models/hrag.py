"""Backend-independent HRAG extraction contracts and fixed v1 vocabulary."""

import math
import re
from hashlib import sha256
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models.assess import AssessSearchFilters
from models.llm import LLMEndpoint


EMBEDDING_CONTENT_LIMIT = 4_000
EXTRACTION_CONTENT_LIMIT = 20_000
HRAG_SCHEMA_VERSION = "v1"

type EntityType = Literal[
    "PER",
    "ORG",
    "GPE",
    "PRODUCT",
    "EVENT",
    "GROUP",
    "MALWARE",
    "TOOL",
    "TACTIC",
    "TECHNIQUE",
    "SECTOR",
    "INDICATOR",
    "VULNERABILITY",
    "CAMPAIGN",
    "INCIDENT",
    "MITIGATION",
    "LOCATION",
    "INFRASTRUCTURE",
    "MOTIVATION",
    "CAPABILITY",
]

ENTITY_DESCRIPTIONS: dict[str, str] = {
    "PER": "An explicitly named person; omit generic roles.",
    "ORG": "A named company, institution, government body, party, or organized body.",
    "GPE": "A named country, state, province, city, or other geopolitical entity.",
    "PRODUCT": "A named product, branded service, platform, or software product.",
    "EVENT": "A named happening other than a cybersecurity campaign or incident.",
    "GROUP": "A named threat actor or intrusion group, not a generic group of people.",
    "MALWARE": "An explicitly named malware family, not a biological virus.",
    "TOOL": "A named offensive or defensive technical tool, identified as such in context.",
    "TACTIC": "An explicitly named adversary objective, not an inferred intention.",
    "TECHNIQUE": "An explicitly named attack technique or tradecraft method.",
    "SECTOR": "An explicitly identified industry or public sector, not an individual company.",
    "INDICATOR": "An explicit technical indicator such as an IP, domain, URL, or file hash.",
    "VULNERABILITY": "An explicitly identified vulnerability, including CVE identifiers.",
    "CAMPAIGN": "An explicitly described coordinated cybersecurity operation.",
    "INCIDENT": "A concrete security occurrence; do not combine separate incidents.",
    "MITIGATION": "An explicitly described defensive or remedial action or control.",
    "LOCATION": "A named geographic place that is not a geopolitical entity, such as a river or mountain range.",
    "INFRASTRUCTURE": "Explicit technical infrastructure; use INDICATOR for individual addresses and PRODUCT for branded services.",
    "MOTIVATION": "An objective explicitly attributed by the source; never infer intent.",
    "CAPABILITY": "An ability explicitly described by the source; never infer abilities from association.",
}

# Endpoint constraints are shared by extraction validation and query compilation.
ACTORS = frozenset({"PER", "ORG", "GROUP"})
OCCURRENCES = frozenset({"EVENT", "CAMPAIGN", "INCIDENT"})
TECHNICAL = frozenset({"MALWARE", "TOOL", "PRODUCT", "INFRASTRUCTURE", "INDICATOR"})
PLACES = frozenset({"GPE", "LOCATION"})
ALL_ENTITIES = frozenset(ENTITY_DESCRIPTIONS)
RELATION_ENDPOINTS: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "USES": (ACTORS | OCCURRENCES | TECHNICAL, TECHNICAL | {"TACTIC", "TECHNIQUE"}),
    "ATTACKS": (ACTORS | {"MALWARE", "CAMPAIGN", "INCIDENT"}, ACTORS | TECHNICAL | PLACES | {"SECTOR"}),
    "TARGETS": (ACTORS | {"MALWARE", "CAMPAIGN", "INCIDENT"}, ACTORS | TECHNICAL | PLACES | {"SECTOR"}),
    "EXPLOITS": (ACTORS | TECHNICAL | {"CAMPAIGN", "INCIDENT"}, frozenset({"VULNERABILITY"})),
    "ABUSES": (ACTORS | {"MALWARE", "CAMPAIGN", "INCIDENT"}, TECHNICAL),
    "ATTRIBUTED_TO": (frozenset({"MALWARE", "CAMPAIGN", "INCIDENT"}), ACTORS),
    "PARTICIPATES_IN": (ACTORS | TECHNICAL | {"INCIDENT"}, OCCURRENCES),
    "LOCATED_IN": (ACTORS | TECHNICAL | PLACES, PLACES),
    "OCCURRED_IN": (OCCURRENCES, PLACES),
    "BELONGS_TO_SECTOR": (ACTORS, frozenset({"SECTOR"})),
    "MITIGATES": (frozenset({"MITIGATION"}), TECHNICAL | {"VULNERABILITY", "TECHNIQUE", "INCIDENT"}),
    "HAS_CAPABILITY": (ACTORS | TECHNICAL, frozenset({"CAPABILITY"})),
    "MOTIVATED_BY": (ACTORS | {"CAMPAIGN", "INCIDENT"}, frozenset({"MOTIVATION"})),
    "ALIAS_OF": (ALL_ENTITIES, ALL_ENTITIES),
    "AFFILIATED_WITH": (ACTORS, ACTORS),
    "OWNS": (ACTORS, ACTORS | TECHNICAL),
    "PRODUCES": (ACTORS, TECHNICAL),
    "SERVES_AS_C2": (TECHNICAL, frozenset({"MALWARE", "CAMPAIGN", "INCIDENT"})),
}


class HragContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceSpan(HragContract):
    """Python Unicode character offsets into the bounded, unchanged content."""

    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str = Field(min_length=1)

    @model_validator(mode="after")
    def valid_range(self) -> Self:
        if self.end <= self.start or self.end - self.start != len(self.quote):
            raise ValueError("Invalid evidence span")
        return self


class ExtractedEntity(HragContract):
    id: str = Field(min_length=1, max_length=128)
    type: EntityType
    name: str = Field(min_length=1, max_length=2048)
    evidence: EvidenceSpan


class ExtractedRelation(HragContract):
    type: str
    source_id: str
    target_id: str
    evidence: EvidenceSpan
    assertion: Literal["affirmed", "negated", "uncertain"] = "affirmed"
    date: str = Field(default="", max_length=128, description="Explicit date phrase from the evidence quote, or empty if absent")


class ExtractionResult(HragContract):
    entities: list[ExtractedEntity] = Field(default_factory=list, max_length=1000)
    relations: list[ExtractedRelation] = Field(default_factory=list, max_length=2000)

    @model_validator(mode="after")
    def valid_graph(self) -> Self:
        by_id = {entity.id: entity for entity in self.entities}
        if len(by_id) != len(self.entities):
            raise ValueError("Duplicate extracted entity ID")
        for relation in self.relations:
            endpoints = RELATION_ENDPOINTS.get(relation.type)
            source = by_id.get(relation.source_id)
            target = by_id.get(relation.target_id)
            if not endpoints or not source or not target:
                raise ValueError("Invalid extracted relationship")
            if source.type not in endpoints[0] or target.type not in endpoints[1]:
                raise ValueError("Invalid relationship endpoint types")
            if relation.type == "ALIAS_OF" and source.type != target.type:
                raise ValueError("Aliases must have the same entity type")
        return self

    def validate_content(self, content: str) -> Self:
        for record in [*self.entities, *self.relations]:
            span = record.evidence
            if content[span.start : span.end] != span.quote:
                raise ValueError("Evidence does not match extraction input")
        for relation in self.relations:
            if relation.date and relation.date not in relation.evidence.quote:
                raise ValueError("Relationship date is absent from its evidence")
        for entity in self.entities:
            if (
                entity.type == "VULNERABILITY"
                and re.fullmatch(r"CVE-\d{4}-\d{4,}", entity.name, re.IGNORECASE)
                and not re.search(r"(?<![\w-])" + re.escape(entity.name) + r"(?![\w-])", entity.evidence.quote, re.IGNORECASE)
            ):
                raise ValueError("Vulnerability identifier is absent from its evidence")
        return self

    def ner_tags(self) -> dict[str, str]:
        """Project compatible tags; omit ambiguous names as standalone NER does."""
        labels: dict[str, set[str]] = {}
        mapping = {"CAMPAIGN": "EVENT", "INCIDENT": "EVENT"}
        existing = {"PER", "ORG", "GPE", "PRODUCT", "EVENT", "GROUP", "MALWARE", "TOOL", "TACTIC", "TECHNIQUE", "SECTOR", "INDICATOR"}
        for entity in self.entities:
            label = mapping.get(entity.type, entity.type)
            labels.setdefault(entity.name, set()).add(label)
        return {name: next(iter(types)) for name, types in labels.items() if len(types) == 1 and types <= existing}


def bounded_content(content: str | None, limit: int) -> str:
    if limit < 1:
        raise ValueError("Content limit must be positive")
    return (content or "")[:limit]


def input_fingerprint(content: str, generation: str) -> str:
    """Generation identifies the model/configuration; secrets are never part of it."""
    return sha256((generation + "\0" + content).encode("utf-8")).hexdigest()


def entity_identity(entity: ExtractedEntity, news_item_id: str, generation: str) -> str:
    """Only CVE identifiers currently qualify for automatic cross-document linking."""
    if entity.type == "VULNERABILITY" and re.fullmatch(r"CVE-\d{4}-\d{4,}", entity.name, re.IGNORECASE):
        return f"cve:{entity.name.upper()}"
    return f"mention:{news_item_id}:{generation}:{entity.id}"


class GraphPlan(HragContract):
    names: list[str] = Field(default_factory=list, max_length=12)
    entity_types: list[EntityType] = Field(default_factory=list, max_length=20)
    relationships: list[str] = Field(default_factory=list, max_length=18)
    hops: int = Field(default=1, ge=0, le=3)
    filters: AssessSearchFilters = Field(default_factory=AssessSearchFilters)

    @field_validator("names")
    @classmethod
    def valid_names(cls, values):
        if any(not value.strip() or len(value) > 200 for value in values):
            raise ValueError("Invalid entity search name")
        return [value.strip().casefold() for value in values]

    @field_validator("relationships")
    @classmethod
    def valid_relationships(cls, values):
        if set(values) - RELATION_ENDPOINTS.keys():
            raise ValueError("Unknown relationship type")
        return values


class EmbeddingResult(HragContract):
    embedding: list[float] = Field(min_length=1, max_length=16000)

    @field_validator("embedding")
    @classmethod
    def valid_vector(cls, values):
        if not all(math.isfinite(value) for value in values) or not any(values):
            raise ValueError("Embedding must be finite and nonzero")
        return values


class IndexSubmission(HragContract):
    token: str = Field(min_length=1, max_length=64)
    fingerprint: str = Field(min_length=64, max_length=64)
    extraction: ExtractionResult | None = None
    vector: EmbeddingResult | None = None
    failed: bool = False


class IndexJob(HragContract):
    id: str
    token: str
    fingerprint: str
    pipeline: Literal["extraction", "embedding"]
    content: str
    endpoint: LLMEndpoint
    dimensions: int = Field(default=0, ge=0, le=16000)
    cached_result: dict | None = None


class EvidenceReference(HragContract):
    citation: str
    work_id: str
    fingerprint: str
    # Each graph path is authorized as a whole, including intermediate assertions.
    support_ids: list[str] = Field(default_factory=list, max_length=4)
    relation_index: int | None = Field(default=None, ge=0)
    path_id: int | None = Field(default=None, ge=1)


class RetrievalEvidence(EvidenceReference):
    branch: Literal["graph", "vector"]
    news_item_id: str
    story_id: str
    title: str
    quote: str
    assertion: Literal["affirmed", "negated", "uncertain"] | None = None
    description: str = ""
    truncated: bool = False


class HragResult(HragContract):
    evidence: list[RetrievalEvidence] = Field(default_factory=list)
    notices: list[str] = Field(default_factory=list)
    filters: dict = Field(default_factory=dict)


def extraction_vocabulary() -> dict:
    return {
        "version": HRAG_SCHEMA_VERSION,
        "entities": ENTITY_DESCRIPTIONS,
        "relationships": {
            name: {"source_types": sorted(source), "target_types": sorted(target)} for name, (source, target) in RELATION_ENDPOINTS.items()
        },
    }


class IndexAction(HragContract):
    action: Literal["backfill", "reconcile", "activate", "reprocess"]
    generation_id: str = Field(default="", max_length=64)

    @model_validator(mode="after")
    def generation_required(self):
        if self.action in {"activate", "reprocess"} and not self.generation_id:
            raise ValueError("Select an indexing generation")
        return self


class IndexGenerationStatus(HragContract):
    id: str
    pipeline: Literal["extraction", "embedding"]
    active: bool
    model: str
    scanned: bool
    counts: dict[str, int]


class IndexStatus(HragContract):
    enabled: bool
    generations: list[IndexGenerationStatus]

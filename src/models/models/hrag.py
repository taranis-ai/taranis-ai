"""Backend-independent HRAG extraction contracts and fixed v1 vocabulary."""

import math
import re
from hashlib import sha256
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models.llm import LLMEndpoint


EMBEDDING_CONTENT_LIMIT = 10_000
EXTRACTION_CONTENT_LIMIT = 20_000
HRAG_SCHEMA_VERSION = "v2"
HRAG_EXTRACTION_SCHEMA_VERSION = "v5"

type HragIndexIntervalMinutes = Annotated[int, Field(ge=0, le=525600)]

type ReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh", "max"]
type ExtractionReasoningEffort = ReasoningEffort | Literal["default"]

EXTRACTION_REASONING_EFFORTS = {
    "default": "Provider default",
    "none": "Disabled (none)",
    "minimal": "Minimal",
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "xhigh": "Extra high",
    "max": "Maximum",
}

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

    @classmethod
    def from_quote(cls, content: str, quote: str) -> Self:
        start = content.find(quote)
        if start < 0:
            raise ValueError("Evidence does not match extraction input")
        return cls(start=start, end=start + len(quote), quote=quote)

    @model_validator(mode="after")
    def valid_range(self) -> Self:
        if self.end <= self.start or self.end - self.start != len(self.quote):
            raise ValueError("Invalid evidence span")
        return self


class EntityMention(HragContract):
    id: str = Field(min_length=1, max_length=128)
    type: EntityType
    name: str = Field(min_length=1, max_length=2048)


class ExtractedEntity(EntityMention):
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


class QuotedRelation(HragContract):
    source_id: str
    target_id: str
    type: str
    quote: str = Field(min_length=1)
    assertion: Literal["affirmed", "negated", "uncertain"]


class CompactExtractionResult(HragContract):
    """LLM-facing contract; persisted evidence spans are resolved locally."""

    entities: list[EntityMention] = Field(default_factory=list, max_length=1000)
    relations: list[QuotedRelation] = Field(default_factory=list, max_length=2000)

    def resolve(self, content: str, *, quarantine_invalid_relations: bool = False) -> ExtractionResult:
        entities = []
        for entity in self.entities:
            if entity.type == "VULNERABILITY" and re.fullmatch(r"CVE-\d{4}-\d{4,}", entity.name, re.IGNORECASE):
                match = re.search(r"(?<![\w-])" + re.escape(entity.name) + r"(?![\w-])", content)
                if match is None:
                    raise ValueError("Vulnerability identifier is absent from extraction input")
                evidence = EvidenceSpan(start=match.start(), end=match.end(), quote=entity.name)
            else:
                evidence = EvidenceSpan.from_quote(content, entity.name)
            entities.append(ExtractedEntity(**entity.model_dump(), evidence=evidence))
        # Entity failures still enter the shared repair path. A malformed proposal
        # must not prevent independent, valid relationships from being verified.
        result = ExtractionResult(entities=entities).validate_content(content)
        by_id = {entity.id: entity for entity in entities}
        relations = []
        for relation in self.relations:
            try:
                resolved = ExtractedRelation(
                    **relation.model_dump(exclude={"quote"}), evidence=EvidenceSpan.from_quote(content, relation.quote)
                )
                endpoints = {key: by_id[key] for key in (relation.source_id, relation.target_id) if key in by_id}
                ExtractionResult(entities=list(endpoints.values()), relations=[resolved]).validate_content(content)
                relations.append(resolved)
            except ValueError:
                if not quarantine_invalid_relations:
                    raise
        return ExtractionResult(entities=result.entities, relations=relations).validate_content(content)


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


class EmbeddingSettings(BaseModel):
    hrag_chunking_enabled: bool = True
    hrag_chunk_size: int = Field(default=2000, ge=500, le=20000)
    hrag_chunk_overlap: int = Field(default=200, ge=0, le=10000)
    hrag_embedding_limit: int = Field(default=EMBEDDING_CONTENT_LIMIT, ge=1, le=200000)
    hrag_vector_limit: int = Field(default=12, ge=1, le=100)
    hrag_chunks_per_item: int = Field(default=3, ge=1, le=100)

    @model_validator(mode="after")
    def valid_overlap(self) -> Self:
        if self.hrag_chunk_overlap * 2 >= self.hrag_chunk_size:
            raise ValueError("Chunk overlap must be less than half the chunk size")
        return self


class TextChunk(HragContract):
    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def valid_span(self) -> Self:
        if self.end <= self.start:
            raise ValueError("Invalid chunk offsets")
        return self


def split_content(content: str, size: int, overlap: int, enabled: bool = True) -> list[TextChunk]:
    """Paragraph/sentence-aware character windows retaining exact source offsets."""
    if size < 1 or overlap < 0 or overlap * 2 >= size:
        raise ValueError("Invalid chunk size or overlap")
    if not content.strip():
        return []
    if not enabled:
        return [TextChunk(start=0, end=len(content))]
    spans = []
    start = 0
    while start < len(content):
        end = min(len(content), start + size)
        if end < len(content):
            minimum = start + (size + overlap) // 2
            paragraph = content.rfind("\n\n", minimum, end)
            if paragraph >= minimum:
                end = paragraph + 2
            else:
                sentences = list(re.finditer(r"[.!?](?=\s)", content[minimum:end]))
                if sentences:
                    end = minimum + sentences[-1].end()
                elif (space := content.rfind(" ", minimum, end)) >= minimum:
                    end = space + 1
        if content[start:end].strip():
            spans.append(TextChunk(start=start, end=end))
        if end == len(content):
            break
        start = end - overlap
    return spans


class EmbeddingResult(HragContract):
    embedding: list[float] = Field(min_length=1, max_length=16000)

    @field_validator("embedding")
    @classmethod
    def valid_vector(cls, values):
        if not all(math.isfinite(value) for value in values) or not any(values):
            raise ValueError("Embedding must be finite and nonzero")
        return values


class ChunkEmbedding(EmbeddingResult, TextChunk):
    pass


class IndexSubmission(HragContract):
    token: str = Field(min_length=1, max_length=64)
    fingerprint: str = Field(min_length=64, max_length=64)
    extraction: ExtractionResult | None = None
    chunks: list[ChunkEmbedding] | None = Field(default=None, max_length=2000)
    failed: bool = False


class IndexJob(HragContract):
    id: str
    token: str
    fingerprint: str
    pipeline: Literal["extraction", "embedding"]
    content: str
    endpoint: LLMEndpoint
    verification_endpoint: LLMEndpoint | None = None
    reasoning_effort: ReasoningEffort | None = None
    dimensions: int = Field(default=0, ge=0, le=16000)
    cached_result: dict | None = None
    chunks: list[TextChunk] = Field(default_factory=list, max_length=2000)

    @model_validator(mode="after")
    def validate_pipeline_endpoints(self) -> Self:
        if self.pipeline == "extraction":
            if self.endpoint.api_format not in {"responses", "chat_completions"} or self.endpoint.processing_mode != "realtime":
                raise ValueError("Extraction requires a realtime generative endpoint")
            if self.verification_endpoint is None or not self.verification_endpoint.is_decisions:
                raise ValueError("Extraction requires a Decisions verification endpoint")
        else:
            if self.endpoint.api_format != "embeddings" or self.endpoint.processing_mode != "realtime":
                raise ValueError("Embedding requires a realtime embedding endpoint")
            if self.dimensions < 1 or not self.chunks:
                raise ValueError("Embedding requires dimensions and source chunks")
            if any(chunk.end > len(self.content) or not self.content[chunk.start : chunk.end].strip() for chunk in self.chunks):
                raise ValueError("Invalid embedding chunk offsets")
        return self


class EvidenceReference(HragContract):
    citation: str
    work_id: str
    fingerprint: str
    # Each graph path is authorized as a whole, including intermediate assertions.
    support_ids: list[str] = Field(default_factory=list, max_length=4)
    relation_index: int | None = Field(default=None, ge=0)
    path_id: int | None = Field(default=None, ge=1)
    chunk_index: int | None = Field(default=None, ge=0)


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
        "entity_types": [{"name": name, "description": description} for name, description in ENTITY_DESCRIPTIONS.items()],
        "relation_types": [
            {"name": name, "source_types": sorted(source), "target_types": sorted(target)}
            for name, (source, target) in RELATION_ENDPOINTS.items()
        ],
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
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    content_limit: int | None = None
    chunking_enabled: bool | None = None


class IndexStatus(HragContract):
    enabled: bool
    generations: list[IndexGenerationStatus]
    configuration_errors: list[str] = Field(default_factory=list)

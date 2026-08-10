from pydantic import BaseModel, ConfigDict, Field, model_validator


class HragEntityType(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    description: str = Field(min_length=1)


class HragRelationType(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    source_types: list[str] = Field(min_length=1)
    target_types: list[str] = Field(min_length=1)


class HragSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(min_length=1)
    entity_types: list[HragEntityType] = Field(min_length=1)
    relation_types: list[HragRelationType] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_references(self) -> "HragSchema":
        entity_names = [entity_type.name for entity_type in self.entity_types]
        if len(entity_names) != len(set(entity_names)):
            raise ValueError("Entity type names must be unique")

        relation_names = [relation_type.name for relation_type in self.relation_types]
        if len(relation_names) != len(set(relation_names)):
            raise ValueError("Relation type names must be unique")

        known_entities = set(entity_names)
        referenced = {
            entity_type for relation_type in self.relation_types for entity_type in relation_type.source_types + relation_type.target_types
        }
        if unknown := sorted(referenced - known_entities):
            raise ValueError(f"Relation constraints reference unknown entity types: {', '.join(unknown)}")
        return self

    def entity_relationship_payload(self) -> dict:
        return {
            "entity_types": [entity_type.model_dump() for entity_type in self.entity_types],
            "relation_types": [relation_type.model_dump() for relation_type in self.relation_types],
        }


DEFAULT_HRAG_SCHEMA = HragSchema(
    version="v1",
    entity_types=[
        HragEntityType(name="ThreatActor", description="A named threat actor or intrusion set."),
        HragEntityType(name="Malware", description="Malicious software or a malware family."),
        HragEntityType(name="Tool", description="A software tool used in an intrusion."),
        HragEntityType(name="Vulnerability", description="A software vulnerability, preferably identified by CVE."),
        HragEntityType(name="Organization", description="An organization, institution, or company."),
        HragEntityType(name="Attack", description="A distinct cybersecurity attack or intrusion event."),
    ],
    relation_types=[
        HragRelationType(name="USES", source_types=["ThreatActor", "Attack", "Malware"], target_types=["Malware", "Tool"]),
        HragRelationType(
            name="EXPLOITS",
            source_types=["ThreatActor", "Attack", "Malware"],
            target_types=["Vulnerability"],
        ),
        HragRelationType(
            name="TARGETS",
            source_types=["ThreatActor", "Attack", "Malware"],
            target_types=["Organization"],
        ),
        HragRelationType(name="ATTRIBUTED_TO", source_types=["Attack", "Malware"], target_types=["ThreatActor"]),
    ],
)

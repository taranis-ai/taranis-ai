"""Analyst input for component-specific OSINT relevance rules."""

from pydantic import BaseModel, Field, field_validator


class TriggerInput(BaseModel):
    phrase: str = Field(min_length=1, max_length=200)
    context: list[str] = Field(default_factory=list, max_length=10)
    enabled: bool = False

    @field_validator("phrase")
    @classmethod
    def normalize_phrase(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("A trigger phrase is required")
        return value

    @field_validator("context")
    @classmethod
    def normalize_context(cls, values: list[str]) -> list[str]:
        phrases = list(dict.fromkeys(" ".join(v.split()) for v in values if v.strip()))
        if any(len(p) > 200 for p in phrases):
            raise ValueError("Context phrases must not exceed 200 characters")
        return phrases


class TriggerCreate(TriggerInput):
    component_id: str


class TriggerSelection(BaseModel):
    trigger_ids: list[str] = Field(min_length=1, max_length=100)
    enabled: bool


class MatchRunInput(BaseModel):
    days: int = Field(default=30, ge=0, le=36500)

"""Analyst input for OSINT relevance rules and intelligence filters."""

from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator


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


class IntelligenceFilters(BaseModel):
    """Filters apply together to one article's associations with one host."""

    page: int = Field(default=1, ge=1)
    asset_id: str = Field(default="", max_length=64)
    group_id: str = Field(default="", max_length=64)
    tag: str = ""
    package: str = Field(default="", max_length=200)
    cve_match: Literal["any", "yes", "no"] = "any"
    package_match: Literal["any", "yes", "no"] = "any"
    cvss_available: Literal["any", "yes", "no"] = "any"
    cvss_min: float | None = Field(default=None, ge=0, le=10, allow_inf_nan=False)
    cvss_max: float | None = Field(default=None, ge=0, le=10, allow_inf_nan=False)

    @field_validator("cvss_min", "cvss_max", mode="before")
    @classmethod
    def empty_score(cls, value):
        return None if value == "" else value

    @field_validator("tag")
    @classmethod
    def normalize_tag(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("package")
    @classmethod
    def trim_package(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def ordered_scores(self) -> Self:
        if self.cvss_min is not None and self.cvss_max is not None and self.cvss_min > self.cvss_max:
            raise ValueError("The minimum CVSS score must not exceed the maximum")
        return self

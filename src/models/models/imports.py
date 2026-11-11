"""Existing versioned transfer formats and their intrinsic validation."""

import csv
import io
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field, JsonValue, TypeAdapter, ValidationInfo

from models.admin import OSINTSource, WordListEntry
from models.base import TaranisBaseModel


class ImportSourceBase(TaranisBaseModel):
    id: str | None = None
    name: str
    description: str = ""
    rank: int = Field(default=0, ge=0, le=5)
    icon: str | None = None
    enabled: bool | None = True
    group_idx: int | str | None = None


class LegacyCollector(TaranisBaseModel):
    type: str


class LegacyParameterKey(TaranisBaseModel):
    key: str


class LegacyParameter(TaranisBaseModel):
    parameter: LegacyParameterKey
    value: JsonValue


class ImportSourceV1(ImportSourceBase):
    collector: LegacyCollector
    parameter_values: list[LegacyParameter] = Field(default_factory=list)


class ImportSourceV2(ImportSourceBase):
    type: str
    parameters: list[dict[str, JsonValue]] | dict[str, JsonValue] | None = None


class ImportSourceGroup(TaranisBaseModel):
    name: str
    description: str | None = ""
    default: bool = False
    key: str | None = None
    osint_sources: list[int | str] = Field(default_factory=list)
    word_lists: list[str] = Field(default_factory=list)


class SourceImportV1(BaseModel):
    version: Literal[1]
    data: list[ImportSourceV1]


class SourceImportV2(BaseModel):
    version: Literal[2]
    data: list[ImportSourceV2]


class SourceImportV3(BaseModel):
    version: Literal[3]
    sources: list[ImportSourceV2]
    groups: list[ImportSourceGroup] = Field(default_factory=list)


class SourceImportV4(BaseModel):
    version: Literal[4]
    sources: list[OSINTSource]
    groups: list[ImportSourceGroup] = Field(default_factory=list)


SourceImport = Annotated[SourceImportV1 | SourceImportV2 | SourceImportV3 | SourceImportV4, Field(discriminator="version")]
SOURCE_IMPORT = TypeAdapter(SourceImport)


class WordListImportRow(TaranisBaseModel):
    name: str = ""
    description: str | None = ""
    usage: int | list[str] = 0
    link: str | None = None
    entries: list[WordListEntry] = Field(default_factory=list)


class WordListImport(BaseModel):
    version: Literal[1]
    data: list[WordListImportRow] = Field(min_length=1)


def csv_word_list(value: str, info: ValidationInfo):
    try:
        reader = csv.reader(io.StringIO(value), csv.Sniffer().sniff(value))
        headers = [header.lower() for header in next(reader)]
        if not 2 <= len(headers) <= 3:
            raise ValueError("Invalid CSV file")
        entries = [dict(zip(headers, row, strict=True)) for row in reader]
    except (csv.Error, StopIteration):
        raise ValueError("Invalid CSV file") from None
    return {"version": 1, "data": [{"name": (info.context or {}).get("filename", ""), "entries": entries}]}


CSV_WORD_LIST = TypeAdapter(Annotated[WordListImport, BeforeValidator(csv_word_list, json_schema_input_type=str)])


class SourcesImported(BaseModel):
    sources: list[str]
    count: int
    message: str


class WordListsImported(BaseModel):
    word_lists: list[str]
    count: int
    message: str


class SkippedUser(BaseModel):
    username: str
    reason: str


class ImportedUser(BaseModel):
    username: str


class UsersImported(BaseModel):
    users: list[ImportedUser]
    count: int
    skipped_users: list[SkippedUser]
    skipped_count: int
    message: str

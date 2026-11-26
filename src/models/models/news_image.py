"""Limits shared by image capture, ingestion and enrichment."""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, HttpUrl


MAX_IMAGE_COUNT = 8
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
MAX_DESCRIPTION_LENGTH = 16_000


def normalize_alt_text(value: str | None) -> str | None:
    return (value or "").replace("\x00", "").strip()[:MAX_DESCRIPTION_LENGTH].rstrip() or None


class CapturedImage(BaseModel):
    source_url: HttpUrl
    alt_text: Annotated[str | None, AfterValidator(normalize_alt_text)] = None
    data: str = Field(min_length=4, max_length=4 * ((MAX_IMAGE_BYTES + 2) // 3), repr=False)


class ImageMetadata(BaseModel):
    id: str
    mime_type: str
    description: str | None = None

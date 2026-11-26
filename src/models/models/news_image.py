"""Limits shared by image capture, ingestion and enrichment."""

from pydantic import BaseModel, Field, HttpUrl


MAX_IMAGE_COUNT = 8
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
MAX_DESCRIPTION_LENGTH = 16_000


class CapturedImage(BaseModel):
    source_url: HttpUrl
    data: str = Field(min_length=4, max_length=4 * ((MAX_IMAGE_BYTES + 2) // 3), repr=False)


class ImageMetadata(BaseModel):
    id: str
    mime_type: str
    description: str | None = None

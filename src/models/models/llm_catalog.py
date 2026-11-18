from typing import Annotated

from pydantic import BaseModel, StringConstraints

from models.llm import LLMAPIFormat, LLMProcessingMode


class LLMModelCatalogQuery(BaseModel):
    api_urls: dict[LLMAPIFormat, Annotated[str, StringConstraints(strip_whitespace=True)]]
    processing_mode: LLMProcessingMode = "realtime"


class LLMModelSuggestion(BaseModel):
    id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    name: str


class OpenRouterCatalogModel(LLMModelSuggestion):
    endpoints: list[str] = []


class OpenRouterCatalog(BaseModel):
    data: list[OpenRouterCatalogModel]

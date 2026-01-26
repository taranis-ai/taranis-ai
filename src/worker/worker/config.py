from typing import Literal

from pydantic import ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    API_KEY: str = "supersecret"
    BOT_API_KEY: str | None = None
    TARANIS_CORE_URL: str = ""
    TARANIS_BASE_PATH: str = "/"
    TARANIS_CORE_HOST: str = "core:8080"
    MODULE_ID: str = "Workers"
    COLORED_LOGS: bool = True
    DEBUG: bool = False
    SSL_VERIFICATION: bool = False
    REQUESTS_TIMEOUT: int = 60
    WORKER_TYPES: list[Literal["Bots", "Collectors", "Presenters", "Publishers", "Connectors", "Misc"]] = [
        "Bots",
        "Collectors",
        "Presenters",
        "Publishers",
        "Connectors",
        "Misc",
    ]
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PASSWORD: str | None = None
    SUMMARY_API_ENDPOINT: str = "http://summary_bot:8000"
    NLP_API_ENDPOINT: str = "http://nlp_bot:8000"
    STORY_API_ENDPOINT: str = "http://story_bot:8000"
    SENTIMENT_ANALYSIS_API_ENDPOINT: str = "http://sentiment_analysis_bot:8000"
    CYBERSEC_CLASSIFIER_API_ENDPOINT: str = "http://cybersec_classifier_bot:8000"
    CYBERSEC_CLASSIFIER_THRESHOLD: float = 0.65

    @field_validator("TARANIS_BASE_PATH", mode="before")
    def ensure_start_and_end_slash(cls, v: str, info: ValidationInfo) -> str:
        # sourcery skip: assign-if-exp, reintroduce-else
        if not v or v == "/":
            return "/"

        return f"/{v.strip('/')}/"

    @model_validator(mode="after")
    def set_taranis_core(self):
        if self.TARANIS_CORE_URL:
            return self
        self.TARANIS_CORE_URL = f"http://{self.TARANIS_CORE_HOST}{self.TARANIS_BASE_PATH}api"
        return self


Config = Settings()

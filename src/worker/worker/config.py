from pydantic_settings import BaseSettings
from typing import Literal, Any
from pydantic import model_validator, ValidationInfo, field_validator
from kombu import Queue


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
    WORKER_TYPES: list[Literal["Bots", "Collectors", "Presenters", "Publishers", "Connectors"]] = [
        "Bots",
        "Collectors",
        "Presenters",
        "Publishers",
        "Connectors",
    ]
    QUEUE_BROKER_SCHEME: Literal["amqp", "amqps"] = "amqp"
    QUEUE_BROKER_HOST: str = "localhost"
    QUEUE_BROKER_PORT: int = 5672
    QUEUE_BROKER_USER: str = "taranis"
    QUEUE_BROKER_PASSWORD: str = "supersecret"
    QUEUE_BROKER_URL: str | None = None
    QUEUE_BROKER_VHOST: str = "/"
    CELERY: dict[str, Any] | None = None
    SUMMARY_API_ENDPOINT: str = "http://summary_bot:8000"
    NLP_API_ENDPOINT: str = "http://nlp_bot:8000"
    STORY_API_ENDPOINT: str = "http://story_bot:8000"
    SENTIMENT_ANALYSIS_API_ENDPOINT: str = "http://sentiment_analysis_bot:8000"
    CYBERSEC_CLASSIFIER_API_ENDPOINT: str = "http://cybersec_classifier_bot:8000"
    CYBERSEC_CLASSIFIER_THRESHOLD: float = 0.65

    @model_validator(mode="after")
    def set_celery(self):
        if self.CELERY and len(self.CELERY) > 1:
            return self
        if self.QUEUE_BROKER_URL:
            broker_url = self.QUEUE_BROKER_URL
        else:
            broker_url = (
                f"{self.QUEUE_BROKER_SCHEME}://{self.QUEUE_BROKER_USER}:{self.QUEUE_BROKER_PASSWORD}"
                f"@{self.QUEUE_BROKER_HOST}:{self.QUEUE_BROKER_PORT}/{self.QUEUE_BROKER_VHOST}"
            )
        task_queues = [Queue("misc")]
        task_queues.extend(Queue(f"{worker_type.lower()}", routing_key=f"{worker_type.lower()}") for worker_type in self.WORKER_TYPES)
        self.CELERY = {
            "broker_url": broker_url,
            "broker_connection_retry_on_startup": True,
            "result_backend": "worker.http_backend:HTTPBackend",
            "broker_connection_retry": False,  # To suppress deprecation warning
            "enable_utc": True,
            "worker_hijack_root_logger": False,
            "task_queues": task_queues,
        }
        return self

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

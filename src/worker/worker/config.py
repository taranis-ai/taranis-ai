import os
import json
from pydantic_settings import BaseSettings
from typing import Literal, Any
from pydantic import model_validator, ValidationError, ValidationInfo, field_validator
from kombu import Queue


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    API_KEY: str = "supersecret"
    TARANIS_CORE_URL: str = ""
    TARANIS_BASE_PATH: str = "/"
    TARANIS_CORE_HOST: str = "core:8080"
    MODULE_ID: str = "Workers"
    COLORED_LOGS: bool = True
    DEBUG: bool = False
    SSL_VERIFICATION: bool = False
    REQUESTS_TIMEOUT: int = 60
    WORKER_TYPES: list[Literal["Bots", "Collectors", "Presenters", "Publishers"]] = ["Bots", "Collectors", "Presenters", "Publishers"]
    QUEUE_BROKER_SCHEME: Literal["amqp", "amqps"] = "amqp"
    QUEUE_BROKER_HOST: str = "localhost"
    QUEUE_BROKER_PORT: int = 5672
    QUEUE_BROKER_USER: str = "taranis"
    QUEUE_BROKER_PASSWORD: str = "supersecret"
    QUEUE_BROKER_URL: str | None = None
    QUEUE_BROKER_VHOST: str = "/"
    CELERY: dict[str, Any] | None = None
    NLP_LANGUAGES: list[str] = ["en", "de"]
    LANGUAGE_MODEL_MAPPING: dict[str, dict[str, str]] = {}
    DEFAULT_NLP_LANGUAGE: str = "en"

    @model_validator(mode="after")
    def check_language_model_mapping(self):
        supported_languages_path = os.path.join(os.path.dirname(__file__), "supported_languages.json")
        with open(supported_languages_path, "r") as file:
            nlp_model_config = json.load(file)

        for lang in self.NLP_LANGUAGES:
            if lang not in nlp_model_config.keys():
                raise ValidationError(f"Language {lang} is not supported. Supported languages are {nlp_model_config.keys()}")

        if self.DEFAULT_NLP_LANGUAGE not in nlp_model_config.keys():
            raise ValidationError(
                f"Default NLP Language {self.DEFAULT_NLP_LANGUAGE} is not supported. Supported languages are {nlp_model_config.keys()}"
            )
        # Populate LANGUAGE_MODEL_MAPPING based on supported languages and fill missing keys
        updated_language_model_mapping = {}
        default_models = nlp_model_config[self.DEFAULT_NLP_LANGUAGE]

        supported_models = ["SUMMARY_BOT", "NLP_BOT", "STORY_BOT"]

        for lang, models in nlp_model_config.items():
            if lang not in self.NLP_LANGUAGES:
                continue
            for supported_model in supported_models:
                if supported_model not in models:
                    models[supported_model] = default_models[supported_model]

            updated_language_model_mapping[lang] = models

        self.LANGUAGE_MODEL_MAPPING = updated_language_model_mapping
        return self

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

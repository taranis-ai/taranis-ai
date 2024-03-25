from pydantic_settings import BaseSettings
from typing import Literal, Any
from pydantic import model_validator
from kombu import Queue


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    API_KEY: str = "supersecret"
    TARANIS_CORE_URL: str = "http://taranis/api"
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
            "beat_scheduler": "worker.scheduler:RESTScheduler",
            "enable_utc": True,
            "worker_hijack_root_logger": False,
            "task_queues": task_queues,
        }
        return self


Config = Settings()

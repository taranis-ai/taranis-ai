from pydantic import BaseSettings
from typing import Literal, Any
from pydantic import validator


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    API_KEY: str = "supersecret"
    TARANIS_NG_CORE_URL: str = "http://taranis"
    MODULE_ID: str = "Workers"
    COLORED_LOGS: bool = True
    DEBUG: bool = False
    SSL_VERIFICATION: bool = False
    WORKER_TYPE: Literal["Bots", "Collectors", "Presenters", "Publishers"] = "Bots"
    QUEUE_BROKER_SCHEME: Literal["amqp", "amqps"] = "amqp"
    QUEUE_BROKER_HOST: str = "localhost"
    QUEUE_BROKER_PORT: int = 5672
    QUEUE_BROKER_USER: str = "taranis"
    QUEUE_BROKER_PASSWORD: str = "supersecret"
    QUEUE_BROKER_VHOST: str = "/"
    CELERY: dict[str, Any] | None = None

    @validator("CELERY", pre=True, always=True)
    def set_celery(cls, value, values):
        if value and len(value) > 1:
            return value
        return {
            "broker_url": f"{values['QUEUE_BROKER_SCHEME']}://{values['QUEUE_BROKER_USER']}:{values['QUEUE_BROKER_PASSWORD']}@{values['QUEUE_BROKER_HOST']}:{values['QUEUE_BROKER_PORT']}/{values['QUEUE_BROKER_VHOST']}",
            "ignore_result": True,
            "broker_connection_retry_on_startup": True,
            "broker_connection_retry": False,  # To suppress deprecation warning
            "beat_scheduler": "worker.scheduler:RESTScheduler",
        }


Config = Settings()

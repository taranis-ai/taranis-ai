from pydantic import model_validator
from pydantic_settings import BaseSettings
from typing import Any, Literal
from datetime import datetime


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    API_KEY: str = "supersecret"
    MODULE_ID: str = "Core"
    DEBUG: bool = False
    SECRET_KEY: str = "supersecret"

    JWT_IDENTITY_CLAIM: str = "sub"
    JWT_ACCESS_TOKEN_EXPIRES: int = 14400

    DB_URL: str = "localhost"
    DB_DATABASE: str = "taranis"
    DB_USER: str = "taranis"
    DB_PASSWORD: str = "supersecret"
    SQLALCHEMY_SCHEMA: str = "postgresql+psycopg2"
    SQLALCHEMY_ECHO: bool = False
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_DATABASE_URI: str | None = None
    COLORED_LOGS: bool = True
    BUILD_DATE: datetime = datetime.now()
    GIT_INFO: dict[str, str] | None = None
    DATA_FOLDER: str = "./taranis_data"

    @model_validator(mode="after")
    def set_sqlalchemy_uri(self) -> "Settings":
        if self.SQLALCHEMY_DATABASE_URI and len(self.SQLALCHEMY_DATABASE_URI) > 1:
            return self
        self.SQLALCHEMY_DATABASE_URI = f"{self.SQLALCHEMY_SCHEMA}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_URL}/{self.DB_DATABASE}"
        return self

    TARANIS_AUTHENTICATOR: Literal["database", "openid", "test"] = "database"

    OPENID_CLIENT_ID: str | None = None
    OPENID_CLIENT_SECRET: str | None = None
    OPENID_LOGOUT_URL: str | None = None
    OPENID_METADATA_URL: str = "http://keycloak/realms/master/.well-known/openid-configuration"
    PRE_SEED_PASSWORD_ADMIN: str = "admin"
    PRE_SEED_PASSWORD_USER: str = "user"

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
        self.CELERY = {
            "broker_url": broker_url,
            "ignore_result": True,
            "broker_connection_retry_on_startup": True,
            "broker_connection_retry": False,  # To suppress deprecation warning
            "enable_utc": True,
        }
        return self


Config = Settings()

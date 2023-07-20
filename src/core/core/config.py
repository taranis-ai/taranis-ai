from pydantic import validator
from pydantic_settings import BaseSettings
from typing import Any, Literal


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
    OpenAPI: str = "static/"

    @validator("SQLALCHEMY_DATABASE_URI", pre=True, always=True)
    def set_sqlalchemy_uri(cls, value, values):
        if value and len(value) > 1:
            return value
        return f"{values['SQLALCHEMY_SCHEMA']}://{values['DB_USER']}:{values['DB_PASSWORD']}@{values['DB_URL']}/{values['DB_DATABASE']}"

    # if "postgresql" in SQLALCHEMY_DATABASE_URI:
    #     DB_POOL_SIZE: int = 10
    #     DB_POOL_RECYCLE: int = 300
    #     DB_POOL_TIMEOUT: int = 5

    #     SQLALCHEMY_ENGINE_OPTIONS: dict = {
    #         "pool_size": DB_POOL_SIZE,
    #         "pool_recycle": DB_POOL_RECYCLE,
    #         "pool_pre_ping": True,
    #         "pool_timeout": DB_POOL_TIMEOUT,
    #     }

    TARANIS_NG_AUTHENTICATOR: str | None = None

    OPENID_CLIENT_ID: str | None = None
    OPENID_CLIENT_SECRET: str | None = None
    OPENID_LOGOUT_URL: str | None = None
    OPENID_METADATA_URL: str = "http://keycloak/realms/master/.well-known/openid-configuration"
    PRE_SEED_PASSWORD_ADMIN: str = "admin"
    PRE_SEED_PASSWORD_USER: str = "user"

    QUEUE_BROKER_SCHEME: Literal["amqp", "amqps"] = "amqp"
    QUEUE_BROKER_HOST: str = "localhost"
    QUEUE_BROKER_PORT: int = 5672
    QUEUE_BROKER_USER: str = "guest"
    QUEUE_BROKER_PASSWORD: str = "guest"
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
        }


Config = Settings()

from pydantic import model_validator, field_validator, ValidationInfo, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Any, Literal
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse


def mask_db_uri(uri: str) -> str:
    parsed = urlparse(uri)

    if parsed.password:
        netloc = f"{parsed.username}:***@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
    else:
        netloc = parsed.netloc

    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    API_KEY: SecretStr = SecretStr("supersecret")
    APPLICATION_ROOT: str = "/"
    MODULE_ID: str = "Core"
    DEBUG: bool = False

    JWT_SECRET_KEY: str = "supersecret"
    JWT_IDENTITY_CLAIM: str = "sub"
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(hours=4)
    JWT_TOKEN_LOCATION: list = ["headers", "cookies"]

    DB_URL: str = "localhost"
    DB_DATABASE: str = "taranis"
    DB_USER: str = "taranis"
    DB_PASSWORD: SecretStr = SecretStr("supersecret")
    SQLALCHEMY_SCHEMA: str = "postgresql+psycopg"
    SQLALCHEMY_ECHO: bool = False
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_DATABASE_URI: str = ""
    SQLALCHEMY_DATABASE_URI_MASK: str | None = None
    SQLALCHEMY_ENGINE_OPTIONS: dict[str, Any] = {}
    SQLALCHEMY_CONNECT_TIMEOUT: int = 10
    SQLALCHEMY_MAX_OVERFLOW: int = 10
    SQLALCHEMY_POOL_SIZE: int = 20
    COLORED_LOGS: bool = True
    BUILD_DATE: datetime = datetime.now()
    GIT_INFO: dict[str, str] | None = None
    DATA_FOLDER: str = "./taranis_data"  # When started with Docker, the path is /app/data
    CACHE_TYPE: str = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT: int = 300
    SSE_URL: str = "http://sse:8088/publish"
    DISABLE_SSE: bool = False
    DISABLE_SCHEDULER: bool = False
    TARANIS_CORE_SENTRY_DSN: str | None = None

    @model_validator(mode="after")  # type: ignore
    def set_sqlalchemy_uri(self) -> "Settings":
        if not self.SQLALCHEMY_DATABASE_URI or len(self.SQLALCHEMY_DATABASE_URI) < 1:
            self.SQLALCHEMY_DATABASE_URI = (
                f"{self.SQLALCHEMY_SCHEMA}://{self.DB_USER}:{self.DB_PASSWORD.get_secret_value()}@{self.DB_URL}/{self.DB_DATABASE}"
            )
        if self.SQLALCHEMY_DATABASE_URI.startswith("sqlite:"):
            self.SQLALCHEMY_ENGINE_OPTIONS.update({"connect_args": {"timeout": self.SQLALCHEMY_CONNECT_TIMEOUT}})
        elif self.SQLALCHEMY_DATABASE_URI.startswith("postgresql:"):
            self.SQLALCHEMY_ENGINE_OPTIONS.update({"connect_args": {"connect_timeout": self.SQLALCHEMY_CONNECT_TIMEOUT}})
        self.SQLALCHEMY_ENGINE_OPTIONS.update(
            {
                "pool_size": self.SQLALCHEMY_POOL_SIZE,
                "max_overflow": self.SQLALCHEMY_MAX_OVERFLOW,
            }
        )
        self.SQLALCHEMY_DATABASE_URI_MASK = mask_db_uri(self.SQLALCHEMY_DATABASE_URI)
        return self

    TARANIS_AUTHENTICATOR: Literal["database", "openid", "external", "dev"] = "database"
    EXTERNAL_AUTH_USER: str = "X-REROUTE-USER"
    EXTERNAL_AUTH_ROLES: str = "X-REROUTE-ROLES"
    EXTERNAL_AUTH_NAME: str = "X-REROUTE-NAME"
    EXTERNAL_AUTH_ORGANIZATION: str = "X-REROUTE-ORGANIZATION"

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
    QUEUE_BROKER_PASSWORD: SecretStr = SecretStr("supersecret")
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
                f"{self.QUEUE_BROKER_SCHEME}://{self.QUEUE_BROKER_USER}:{self.QUEUE_BROKER_PASSWORD.get_secret_value()}"
                f"@{self.QUEUE_BROKER_HOST}:{self.QUEUE_BROKER_PORT}/{self.QUEUE_BROKER_VHOST}"
            )
        self.CELERY = {
            "broker_url": broker_url,
            "create_missing_queues": True,
            "broker_connection_retry_on_startup": True,
            "broker_connection_retry": False,  # To suppress deprecation warning
            "enable_utc": True,
        }
        return self

    @field_validator("JWT_SECRET_KEY", "API_KEY", mode="before")
    def check_non_empty_string_or_secret(cls, v, info: ValidationInfo) -> str | SecretStr:
        value = v.get_secret_value() if isinstance(v, SecretStr) else v
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{info.field_name} must be a non-empty string")
        return v

    @field_validator("APPLICATION_ROOT", mode="before")
    def ensure_start_and_end_slash(cls, v: str, info: ValidationInfo) -> str:
        if not v or v == "/":
            return "/"

        return f"/{v.strip('/')}/"


Config = Settings()

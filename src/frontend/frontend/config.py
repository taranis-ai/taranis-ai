from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator, ValidationInfo
from datetime import datetime


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APPLICATION_ROOT: str = "/frontend"
    MODULE_ID: str = "Frontend"
    DEBUG: bool = False

    JWT_SECRET_KEY: str = "supersecret"
    JWT_IDENTITY_CLAIM: str = "sub"
    JWT_ACCESS_TOKEN_EXPIRES: int = 14400
    JWT_TOKEN_LOCATION: list = ["headers", "cookies"]
    JWT_ACCESS_COOKIE_NAME: str = "access_token_cookie"
    JWT_COOKIE_CSRF_PROTECT: bool = True
    JWT_CSRF_IN_COOKIES: bool = True
    JWT_CSRF_METHODS: list = ["POST", "PUT", "PATCH", "DELETE"]
    COLORED_LOGS: bool = True
    BUILD_DATE: datetime = datetime.now()
    GIT_INFO: dict[str, str] | None = None
    TARANIS_CORE_URL: str = "http://local.taranis.ai/api"
    TARANIS_CORE_HOST: str = "http://local.taranis.ai"
    TARANIS_BASE_PATH: str = "/"
    SSL_VERIFICATION: bool = False
    REQUESTS_TIMEOUT: int = 60
    # BABEL_DEFAULT_LOCALE: str = "en"
    # BABEL_DEFAULT_TIMEZONE: str = "UTC"
    CACHE_TYPE: str = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT: int = 300
    CACHE_KEY_PREFIX: str = "taranis_frontend"

    @field_validator("TARANIS_BASE_PATH", mode="before")
    def ensure_start_and_end_slash(cls, v: str, info: ValidationInfo) -> str:
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

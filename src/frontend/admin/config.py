from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator, ValidationInfo
from datetime import datetime


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APPLICATION_ROOT: str = "/"
    MODULE_ID: str = "Frontend"
    DEBUG: bool = False

    JWT_IDENTITY_CLAIM: str = "sub"
    JWT_ACCESS_TOKEN_EXPIRES: int = 14400
    JWT_TOKEN_LOCATION: list = ["headers", "cookies"]
    JWT_ACCESS_COOKIE_NAME: str = "access_token_cookie"
    COLORED_LOGS: bool = True
    BUILD_DATE: datetime = datetime.now()
    GIT_INFO: dict[str, str] | None = None
    CACHE_TYPE: str = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT: int = 300
    TARANIS_CORE_URL: str = "http://local.taranis.ai/api"
    TARANIS_CORE_HOST: str = ""
    TARANIS_BASE_PATH: str = "/"
    SSL_VERIFICATION: bool = False
    REQUESTS_TIMEOUT: int = 60

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

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    API_KEY: str = "supersecret"
    TARANIS_NG_CORE_URL: str = "http://taranis"
    MODULE_ID: str = "Workers"
    COLORED_LOGS: bool = True
    DEBUG: bool = False
    WORKER_TYPE: Literal["Bots", "Collectors", "Presenters", "Publishers"] = "Bots"


@lru_cache()
def get_settings():
    return Settings()

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    API_KEY: str = "supersecret"
    SSL_VERIFICATION: bool = False
    TARANIS_NG_CORE_URL: str = "http://taranis"
    MODULE_ID: str = "Bots"
    COLORED_LOGS: bool = True
    DEBUG: bool = False

    NODE_NAME: str = "MyBot"
    NODE_DESCRIPTION: str = ""
    NODE_URL: str = "http://bots"
    BOTS_LOADABLE_BOTS: list[str] = ["Analyst", "Grouping", "NLP", "Tagging"]
    SYSLOG_ADDRESS: tuple[str, int] | None = None
    GUNICORN: bool = "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")


settings = Settings()

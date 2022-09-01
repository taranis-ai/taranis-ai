from typing import List
from pydantic import BaseSettings


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    API_KEY: str
    SSL_VERIFICATION: bool = False
    TARANIS_NG_CORE_URL: str = "http://taranis"
    COLLECTOR_URL: str = "http://collectors"
    MODULE_ID: str = "Collectors"
    COLLECTOR_LOADABLE_COLLECTORS: List[str] = ["RSS", "Email", "Slack", "Twitter", "Web", "Atom", "Manual"]


Config = Settings()

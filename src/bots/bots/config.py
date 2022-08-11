from pydantic import BaseSettings


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    API_KEY: str
    SSL_VERIFICATION: bool = False
    TARANIS_NG_CORE_URL: str = "http://taranis"
    MODULE_ID: str = "Bots"
    # BOTS_LOADABLE_BOTS: List[str] = ["Analyst", "Grouping", "NLP", "Tagging", "Wordlist"]


Config = Settings()

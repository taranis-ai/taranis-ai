from pydantic import BaseSettings


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    API_KEY: str = "supersecret"
    SSL_VERIFICATION: bool = False
    MODULE_ID: str = "Presenters"
    COLORED_LOGS: bool = True
    DEBUG: bool = False


Config = Settings()

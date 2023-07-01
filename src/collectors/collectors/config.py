from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    API_KEY: str = "supersecret"
    NODE_NAME: str = "MyCollector"
    NODE_DESCRIPTION: str = ""
    SSL_VERIFICATION: bool = False
    TARANIS_NG_CORE_URL: str = "http://taranis"
    NODE_URL: str = "http://collectors"
    MODULE_ID: str = "Collectors"
    COLORED_LOGS: bool = True
    DEBUG: bool = False
    COLLECTOR_LOADABLE_COLLECTORS: list[str] = ["RSS", "Email", "Slack", "Twitter", "Web", "Atom", "Manual"]


Config = Settings()

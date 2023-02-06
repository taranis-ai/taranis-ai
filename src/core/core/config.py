from pydantic import BaseSettings, validator


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
    REDIS_URL: str = "redis://localhost"

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
    OPENID_METADATA_URL: str = "http://keycloak/realms/master/.well-known/openid-configuration"


Config = Settings()

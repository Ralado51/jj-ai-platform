from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "JJ AI Platform API"
    app_version: str = "0.1.0"
    environment: str = "development"

    database_url: str = (
        "postgresql+psycopg://jjplatform:jjplatform@postgres:5432/jjplatform"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

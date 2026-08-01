from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "JJ AI Platform API"
    app_version: str = "0.1.0"
    environment: str = "development"

    database_url: str = (
        "postgresql+psycopg://jjplatform:jjplatform@postgres:5432/jjplatform"
    )

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    password_reset_expire_minutes: int = 30

    frontend_url: str = "https://jjaiplatform.jjnetwork.com.br"
    smtp_host: str = "smtp.hostinger.com"
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_ssl: bool = True

    s3_endpoint_url: str = "http://minio:9000"
    s3_public_endpoint_url: str = "https://files.jjnetwork.com.br"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "jj-ai-projects"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False
    s3_presigned_url_expire_seconds: int = 900

    embedding_provider: str = "ollama"

    ollama_base_url: str = "http://ollama:11434"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_embedding_dimensions: int = 768
    ollama_timeout_seconds: float = 120.0
    ollama_chat_model: str = "qwen2.5:3b"
    ollama_chat_timeout_seconds: float = 180.0
    ollama_chat_temperature: float = 0.2
    ollama_content_model: str = ""
    ollama_rag_model: str = ""
    ollama_coding_model: str = ""
    ollama_summarization_model: str = ""
    ollama_general_model: str = ""

    rag_retrieval_top_k: int = 10
    rag_max_context_characters: int = 5000

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536
    openai_timeout_seconds: float = 60.0

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

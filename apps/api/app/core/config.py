"""Application Configuration using Pydantic Settings."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        enable_decoding=False,
    )

    # === APP ===
    APP_ENV: Literal["development", "testing", "staging", "production"] = "development"
    DEBUG: bool = True
    VERSION: str = "0.1.0"

    # === DATABASE ===
    DATABASE_URL: str = "postgresql+asyncpg://vie_history:vie_history_secret@localhost:12703/vie_history"
    SYNC_DATABASE_URL: str = "postgresql://vie_history:vie_history_secret@localhost:12703/vie_history"

    # === REDIS ===
    REDIS_URL: str = "redis://localhost:12704/0"

    # === QDRANT ===
    QDRANT_URL: str = "http://localhost:12705"
    QDRANT_COLLECTION: str = "historiai_chunks"
    QDRANT_VECTOR_SIZE: int = 384

    # === SECURITY ===
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 * 24 * 60  # 30 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALGORITHM: str = "HS256"

    # === CORS ===
    CORS_ORIGINS: list[str] = ["http://localhost:12702", "http://localhost:3000"]

    # === LLM ===
    LLM_PROVIDER: Literal["openai", "anthropic", "openrouter", "ollama", "gemini", "groq"] = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"

    # === EMBEDDING ===
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_BATCH_SIZE: int = 32
    # Vietnamese-specific model (set to override the default)
    VIETNAMESE_EMBEDDING_MODEL: str = "AITeamVN/Vietnamese_Embedding_v2"
    VIETNAMESE_EMBEDDING_DIMENSION: int = 1024
    VIETNAMESE_EMBEDDING_BATCH_SIZE: int = 16
    # Vietnamese-specific cross-encoder reranker
    VIETNAMESE_RERANKER_MODEL: str = "AITeamVN/Vietnamese_Reranker"

    # === STORAGE ===
    STORAGE_PATH: Path = Path("./storage")
    MAX_UPLOAD_SIZE_MB: int = 50

    # === INGESTION ===
    FETCH_TIMEOUT_SECONDS: int = 30
    FETCH_MAX_RETRIES: int = 3
    MIN_CONTENT_LENGTH: int = 500
    MIN_BOILERPLATE_RATIO: float = 0.3
    CHUNK_SIZE_TOKENS: int = 512
    CHUNK_OVERLAP_TOKENS: int = 50

    SSRF_BLOCKED_RANGES: list[str] = [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "127.0.0.0/8",
        "0.0.0.0/8",
        "169.254.0.0/16",
        "localhost",
    ]

    # === RQ WORKERS ===
    RQ_QUEUE_NAME: str = "ingest-queue"
    RQ_RESULT_TTL: int = 3600

    # === LOGGING ===
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    LOG_FORMAT: Literal["json", "text"] = "json"

    # === RATE LIMITING ===
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, ge=1, le=10000)

    # === PIPELINE FEATURE FLAGS ===
    ENABLE_HYBRID: bool = True
    ENABLE_RERANKER: bool = True
    ENABLE_GRAPH: bool = True
    ENABLE_VERIFICATION: bool = True

    # === MEILISEARCH (BM25) ===
    MEILISEARCH_URL: str = "http://localhost:12707"
    MEILISEARCH_MASTER_KEY: str = "meili_master_key_secret"
    MEILISEARCH_INDEX: str = "historiai_chunks"

    # === NEO4J ===
    NEO4J_URL: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "vie_history_neo4j_secret"

    # === LANGFUSE (LLM Observability) ===
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_HOST: str = "http://localhost:3001"
    LANGFUSE_ENABLED: bool = False

    # === SENTRY ===
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    # === OPENTELEMETRY / OTLP ===
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    OTEL_EXPORTER_OTLP_TLS: bool = True

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string."""
        if isinstance(v, str):
            return [url.strip() for url in v.split(",") if url.strip()]
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if v == "change-me-in-production" and os.environ.get("APP_ENV") == "production":
            raise ValueError("SECRET_KEY must be changed in production")
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("NEO4J_PASSWORD")
    @classmethod
    def validate_neo4j_password(cls, v: str) -> str:
        if v == "vie_history_neo4j_secret" and os.environ.get("APP_ENV") == "production":
            raise ValueError("Default Neo4j password must be changed in production")
        return v

    @field_validator("DATABASE_URL", "REDIS_URL", "QDRANT_URL", "MEILISEARCH_URL")
    @classmethod
    def validate_urls(cls, v: str) -> str:
        if v and not v.startswith(("http://", "https://", "postgresql://", "postgresql+asyncpg://", "redis://", "bolt://")):
            raise ValueError(f"Invalid URL format: {v[:50]}...")
        return v

    @field_validator("SSRF_BLOCKED_RANGES", mode="before")
    @classmethod
    def parse_blocked_ranges(cls, v):
        """Parse SSRF_BLOCKED_RANGES from comma-separated string."""
        if isinstance(v, str):
            return [ip.strip() for ip in v.split(",") if ip.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    def get_llm_config(self) -> dict:
        """Get LLM configuration based on provider."""
        configs = {
            "openai": {
                "api_key": self.OPENAI_API_KEY,
                "model": self.OPENAI_MODEL,
                "base_url": self.OPENAI_BASE_URL,
            },
            "anthropic": {
                "api_key": self.ANTHROPIC_API_KEY,
                "model": self.ANTHROPIC_MODEL,
            },
            "openrouter": {
                "api_key": self.OPENROUTER_API_KEY,
                "base_url": self.OPENROUTER_BASE_URL,
            },
            "ollama": {
                "base_url": self.OLLAMA_BASE_URL,
                "model": self.OLLAMA_MODEL,
            },
            "gemini": {
                "api_key": os.environ.get("GEMINI_API_KEY", ""),
                "model": "gemini-2.0-flash",
            },
            "groq": {
                "api_key": os.environ.get("GROQ_API_KEY", ""),
                "base_url": "https://api.groq.com/openai/v1",
                "model": "llama-3.3-70b-versatile",
            },
        }
        return configs.get(self.LLM_PROVIDER, {})


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# === SHARED INSTANCE ===
settings = get_settings()

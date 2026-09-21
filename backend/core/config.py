"""AEGIS AI — Core Configuration Module
Loads environment variables and validates platform configuration using Pydantic Settings.
"""


from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # General Application
    APP_NAME: str = "AEGIS AI"
    APP_ENV: str = "development"  # development, staging, production, test
    API_V1_STR: str = "/api/v1"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Cryptography & JWT Security
    SECRET_KEY: str = "dev_secret_key_change_in_production_99a38f7e31d479108bfce920e8b23c"
    JWT_SECRET: str = "dev_jwt_secret_change_in_production_418a0b5f54316d24a0d93ea76cf23"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./aegis_ai.db"
    DATABASE_URL_SYNC: str = "sqlite:///./aegis_ai.db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 2
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        v = v.strip()
        if v.startswith("postgres://"):
            v = "postgresql+asyncpg://" + v[len("postgres://"):]
        elif v.startswith("postgresql://") and not v.startswith("postgresql+"):
            v = "postgresql+asyncpg://" + v[len("postgresql://"):]
        if "sslmode=require" in v:
            v = v.replace("sslmode=require", "ssl=require")
        elif "sslmode=prefer" in v:
            v = v.replace("sslmode=prefer", "ssl=prefer")
        return v

    @field_validator("DATABASE_URL_SYNC", mode="before")
    @classmethod
    def normalize_database_url_sync(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        v = v.strip()
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://"):]
        elif v.startswith("postgresql+asyncpg://"):
            v = "postgresql://" + v[len("postgresql+asyncpg://"):]
        return v

    # Cache & Redis (Optional)
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = False

    # AI & LLM Providers: "gemini" | "openai" | "mock"
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-1.5-flash"
    LLM_API_KEY: str = ""
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 4096

    # OpenAI-Compatible Fallback
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # Embeddings: "gemini" | "openai" | "local"
    EMBEDDING_PROVIDER: str = "local"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # Storage: "local" | "s3"
    STORAGE_PROVIDER: str = "local"
    LOCAL_STORAGE_PATH: str = "./backend/storage"

    # Network & CORS
    CORS_ORIGINS: list[str] | str = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Rate Limiting & Safety
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    MAX_UPLOAD_SIZE_MB: int = 25

    # Observability
    LOG_LEVEL: str = "INFO"
    ENABLE_METRICS: bool = True

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def is_testing(self) -> bool:
        return self.APP_ENV.lower() == "test"


# Global cached settings instance
settings = Settings()

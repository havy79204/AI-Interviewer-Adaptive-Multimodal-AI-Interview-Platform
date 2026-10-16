"""
AI Interviewer - Main application configuration
"""

from functools import lru_cache
from math import isfinite
from pathlib import Path
from typing import Any, Optional

from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_LEGACY_DOTENV_KEYS = frozenset(
    {
        "OPENAI_API_KEY",
        "SENTRY_ENVIRONMENT",
        "SENTRY_TRACES_SAMPLE_RATE",
        "PROMETHEUS_PORT",
        "PROMETHEUS_ENABLED",
        "RETRIEVAL_TEMPERATURE",
        "RERANKER_MODEL",
        "CORS_ORIGINS",
        "RATE_LIMIT_ENABLED",
        "RATE_LIMIT_REQUESTS",
        "RATE_LIMIT_PERIOD",
        "BROWSER_AGENT_ENABLED",
        "BROWSER_HEADLESS",
        "BROWSER_TIMEOUT",
        "BROWSER_ALLOWED_DOMAINS",
        "EVALUATION_ENABLED",
        "SYNTHETIC_DATASET_SIZE",
        "GOLDEN_DATASET_PATH",
        "REGRESSION_BASELINE",
        "DOCKER_REGISTRY",
        "DOCKER_IMAGE_TAG",
        "KUBERNETES_NAMESPACE",
        "KUBERNETES_ENVIRONMENT",
        "LOG_FORMAT",
        "LOG_FILE",
        "DEBUG_SQL",
        "DEBUG_RAG",
        "SENTRY_DEBUG",
    }
)


class _LegacyAwareDotEnvSettingsSource(DotEnvSettingsSource):
    """Ignore known obsolete local dotenv keys while rejecting new typos."""

    def __call__(self) -> dict[str, Any]:
        data = super().__call__()
        field_names = self.settings_cls.model_fields
        unsupported = sorted(
            key
            for key in data
            if key not in field_names and key not in _LEGACY_DOTENV_KEYS
        )
        if unsupported:
            raise ValueError(
                "Unsupported .env variables: " + ", ".join(unsupported)
            )
        for key in _LEGACY_DOTENV_KEYS:
            data.pop(key, None)
        return data


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="forbid",
        hide_input_in_errors=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        strict_dotenv_settings = _LegacyAwareDotEnvSettingsSource(
            settings_cls,
            env_file=getattr(dotenv_settings, "env_file", _PROJECT_ROOT / ".env"),
            env_file_encoding=getattr(dotenv_settings, "env_file_encoding", "utf-8"),
            case_sensitive=getattr(dotenv_settings, "case_sensitive", True),
        )
        return (
            init_settings,
            env_settings,
            strict_dotenv_settings,
            file_secret_settings,
        )

    # Application
    APP_NAME: str = "AI Interviewer"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development", alias="ENVIRONMENT")
    DEBUG: bool = False
    LOG_LEVEL: str = "info"

    # API
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Database
    # Default is SQLite for local/dev reliability; set DATABASE_URL to a PostgreSQL DSN
    # in production environments where a managed database is available.
    DATABASE_URL: str = "sqlite:///./storage/ai_interviewer.db"
    SQLALCHEMY_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 3600
    REDIS_TIMEOUT_SECONDS: float = 2.0
    REDIS_SESSION_TTL_SECONDS: int = 300
    REDIS_LOCK_TTL_SECONDS: int = 30
    REDIS_LOCK_ACQUIRE_TIMEOUT_SECONDS: float = 2.0

    # PostgreSQL / production pool settings
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # Security / rate limiting
    AUTH_RATE_LIMIT: int = 10
    INTERVIEW_RATE_LIMIT: int = 20
    VOICE_RATE_LIMIT: int = 60
    LLM_JOB_RATE_LIMIT: int = 5

    # Observability
    OTEL_SERVICE_NAME: str = "ai-interviewer"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENABLE_DEV_ADMIN_BOOTSTRAP: bool = False
    BOOTSTRAP_ADMIN_EMAIL: str = ""
    BOOTSTRAP_ADMIN_PASSWORD: str = ""

    # CORS
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # LLM Providers
    LLM_PROVIDER: str = "none"
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    LLM_TIMEOUT_SECONDS: float = Field(default=20.0, gt=0, le=300)
    LLM_MAX_RETRIES: int = Field(default=1, ge=0, le=5)
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_MAX_TOKENS: int = Field(default=2000, gt=0)

    RUN_LIVE_AI_TESTS: bool = False
    RUN_LIVE_AI_E2E: bool = False
    LIVE_AI_E2E_DATABASE_URL: str = "sqlite:///./storage/live_ai_e2e_isolated.db"

    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-opus-20240229"

    # Embeddings
    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    EMBEDDING_TIMEOUT_SECONDS: float = 10.0
    QWEN_EMBEDDING_MODEL_PATH: str = "Qwen/Qwen3-Embedding-0.6B"
    QWEN_EMBEDDING_REVISION: str = "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"

    # Voice Services
    ELEVEN_LABS_API_KEY: str = ""
    ELEVEN_LABS_VOICE_ID: str = "default"
    ASSEMBLY_AI_API_KEY: str = ""

    # Voice Settings
    VAD_THRESHOLD: float = 0.5
    VAD_SAMPLE_RATE: int = 16000
    STT_LANGUAGE: str = "en-US"
    TTS_SPEED: float = 1.0
    VOICE_ENABLED: bool = True
    VOICE_MAX_AUDIO_CHUNK_BYTES: int = 64 * 1024
    VOICE_MAX_BUFFER_BYTES: int = 2 * 1024 * 1024
    VOICE_MAX_UTTERANCE_SECONDS: int = 120
    VOICE_WS_MAX_MESSAGE_BYTES: int = 128 * 1024
    VOICE_WS_IDLE_TIMEOUT_SECONDS: int = 300
    VAD_PROVIDER: str = "fake"
    STT_PROVIDER: str = "fake"
    STT_MODEL: str = "local-fake"
    STT_TIMEOUT_SECONDS: float = 20.0
    STT_MAX_RETRIES: int = 1
    TTS_PROVIDER: str = "fake"
    TTS_MODEL: str = "local-fake"
    TTS_TIMEOUT_SECONDS: float = 20.0
    TTS_MAX_RETRIES: int = 1
    VOICE_TELEMETRY_ENABLED: bool = True

    # RAG Configuration
    VECTOR_STORE_PROVIDER: str = "sqlalchemy_json"
    VECTOR_STORE_DIMENSION: int = 1536
    VECTOR_SIMILARITY_THRESHOLD: float = 0.7
    RETRIEVAL_TOP_K: int = 5
    RETRIEVAL_STRATEGY: str = "hybrid"
    RERANKER_TOP_K: int = 3
    RERANKER_THRESHOLD: float = 0.5
    RAG_DEMO_CORPUS_VERSION: str = "demo-v1"

    # Interview Configuration
    DEFAULT_INTERVIEW_DURATION: int = 1800  # 30 minutes
    DEFAULT_NUM_QUESTIONS: int = 8
    DEFAULT_DIFFICULTY: str = "medium"
    TURN_PROCESSING_LEASE_SECONDS: int = 300
    MIN_CONFIDENCE_THRESHOLD: float = 0.6
    FAIRNESS_CHECK_ENABLED: bool = True

    # Observability
    SENTRY_DSN: Optional[str] = None
    LANGWATCH_API_KEY: Optional[str] = None
    LANGWATCH_ENABLED: bool = True

    # Feature Flags
    ENABLE_VOICE_MODE: bool = True
    ENABLE_VIDEO_MODE: bool = False
    ENABLE_BROWSER_AGENT: bool = True
    ENABLE_RAG_RETRIEVAL: bool = True
    ENABLE_STREAMING: bool = True

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 3600

    # Storage
    STORAGE_TYPE: str = "local"
    STORAGE_PATH: str = "./storage"

    @field_validator("LLM_PROVIDER")
    @classmethod
    def validate_llm_provider(cls, value: str) -> str:
        provider = value.strip().lower()
        if provider not in {"none", "openai", "ollama"}:
            raise ValueError("LLM_PROVIDER must be one of: 'none', 'openai', 'ollama'")
        return provider

    @field_validator("LLM_TIMEOUT_SECONDS")
    @classmethod
    def validate_finite_llm_timeout(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("LLM_TIMEOUT_SECONDS must be finite")
        return value

    @field_validator("OPENAI_MODEL", "OPENAI_BASE_URL")
    @classmethod
    def validate_non_empty_llm_setting(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("LLM model and base URL must not be empty")
        return value


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()

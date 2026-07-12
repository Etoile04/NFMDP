"""Application configuration via environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    cors_origins: list[str] = ["http://localhost:3000"]
    vlm_api_url: str = "http://localhost:8001"
    vlm_api_key: str = ""
    vlm_timeout_seconds: int = 120
    vlm_max_retries: int = 2
    ocr_fallback_enabled: bool = True
    extraction_max_file_size_mb: int = 100
    extraction_max_pages: int = 500

    database_url: str = "postgresql://supabase_admin:postgres@localhost:54322/postgres"

    model_config = {"env_prefix": "NFM_"}


settings = Settings()

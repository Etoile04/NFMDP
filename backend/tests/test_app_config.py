"""Tests for app factory, config, and database pool lifecycle."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from nfm_backend.app import create_app
from nfm_backend.config import Settings

# ---------------------------------------------------------------------------
# config.py
# ---------------------------------------------------------------------------


class TestSettings:
    def test_defaults(self) -> None:
        s = Settings(_env_file=None)
        assert s.cors_origins == ["http://localhost:3000"]
        assert s.vlm_api_url == "http://localhost:8001"
        assert s.vlm_api_key == ""
        assert s.vlm_timeout_seconds == 120
        assert s.vlm_max_retries == 2
        assert s.ocr_fallback_enabled is True
        assert s.extraction_max_file_size_mb == 100
        assert s.extraction_max_pages == 500

    def test_custom_database_url(self) -> None:
        s = Settings(
            database_url="postgresql://user:pass@host:5432/db",
            _env_file=None,
        )
        assert s.database_url == "postgresql://user:pass@host:5432/db"

    def test_env_prefix(self) -> None:
        s = Settings(_env_file=None)
        assert s.model_config.get("env_prefix") == "NFM_"


# ---------------------------------------------------------------------------
# app.py
# ---------------------------------------------------------------------------


class TestCreateApp:
    def test_creates_fastapi_app(self) -> None:
        settings = Settings(_env_file=None)
        app = create_app(settings=settings)
        assert app.title == "NFM Extraction API"
        assert app.version == "4.0.0"
        assert app.docs_url == "/api/docs"
        assert app.openapi_url == "/api/openapi.json"

    def test_default_settings(self) -> None:
        app = create_app()
        assert app.title == "NFM Extraction API"

    def test_cors_middleware_configured(self) -> None:
        settings = Settings(
            cors_origins=["https://example.com"],
            _env_file=None,
        )
        app = create_app(settings=settings)
        # Middleware is configured via user_middleware
        assert len(app.user_middleware) >= 1


# ---------------------------------------------------------------------------
# database.py
# ---------------------------------------------------------------------------


class TestDatabasePool:
    @pytest.mark.asyncio
    async def test_get_pool_returns_singleton(self) -> None:
        mock_pool = MagicMock()

        from nfm_backend.services import database as db_mod

        db_mod._pool = mock_pool
        pool = await db_mod.get_pool()
        assert pool is mock_pool

    @pytest.mark.asyncio
    async def test_close_pool(self) -> None:
        mock_pool = MagicMock()
        mock_pool.close = AsyncMock()

        from nfm_backend.services import database as db_mod

        db_mod._pool = mock_pool
        await db_mod.close_pool()

        mock_pool.close.assert_called_once()
        assert db_mod._pool is None

    @pytest.mark.asyncio
    async def test_close_pool_noop_when_none(self) -> None:
        from nfm_backend.services import database as db_mod

        db_mod._pool = None
        await db_mod.close_pool()
        assert db_mod._pool is None

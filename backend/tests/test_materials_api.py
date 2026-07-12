"""Tests for /api/v1/materials, /api/v1/sources, /api/v1/properties endpoints.

Mocks asyncpg pool to test endpoint logic without a real database.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from nfm_backend.api.v1.materials import (
    _record_to_dict,
    get_material,
    get_property,
    get_source,
    list_materials,
    list_properties,
    list_sources,
)

SAMPLE_SOURCE_ID = uuid4()
SAMPLE_MATERIAL_ID = uuid4()
SAMPLE_PROPERTY_ID = uuid4()
SAMPLE_TIMESTAMP = datetime(2026, 1, 15, 12, 0, 0)


def _make_source_row(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "id": SAMPLE_SOURCE_ID,
        "title": "UO2 Sintering Study",
        "doi": "10.1234/uo2",
        "journal": "J. Nucl. Mater.",
        "year": 2025,
        "source_type": "journal_article",
        "url": "https://doi.org/10.1234/uo2",
        "created_at": SAMPLE_TIMESTAMP,
    }
    defaults.update(overrides)
    return defaults


def _make_material_row(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "id": SAMPLE_MATERIAL_ID,
        "name": "UO2",
        "name_zh": "二氧化铀",
        "chemical_formula": "UO2",
        "material_type": "ceramic",
        "crystal_structure": "fluorite",
        "density_kg_m3": 10970.0,
        "melting_point_k": 3138.0,
        "description": "Nuclear fuel material",
        "category_id": uuid4(),
        "created_at": SAMPLE_TIMESTAMP,
    }
    defaults.update(overrides)
    return defaults


def _make_property_row(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "id": SAMPLE_PROPERTY_ID,
        "property_type_id": uuid4(),
        "material_id": SAMPLE_MATERIAL_ID,
        "dataset_id": uuid4(),
        "data_source_id": SAMPLE_SOURCE_ID,
        "value_type": "scalar",
        "value_scalar": 10970.0,
        "unit": "kg/m³",
        "uncertainty_value": 10.0,
        "uncertainty_type": "absolute",
        "conditions": '{"temperature": "298K"}',
        "confidence": "high",
        "method": "experimental",
        "notes": "Room temperature",
        "review_status": "approved",
        "created_at": SAMPLE_TIMESTAMP,
    }
    defaults.update(overrides)
    return defaults


class TestRecordToDict:
    def test_simple_columns(self) -> None:
        record = _make_source_row()
        columns = ["id", "title", "doi"]
        result = _record_to_dict(record, columns)
        assert result["id"] == SAMPLE_SOURCE_ID
        assert result["title"] == "UO2 Sintering Study"

    def test_jsonb_column_deserialized(self) -> None:
        record = _make_property_row()
        columns = ["conditions"]
        result = _record_to_dict(record, columns)
        assert isinstance(result["conditions"], dict)
        assert result["conditions"]["temperature"] == "298K"

    def test_jsonb_column_invalid_json(self) -> None:
        record: dict[str, Any] = {"conditions": "not-valid-json"}
        result = _record_to_dict(record, ["conditions"])
        assert isinstance(result["conditions"], str)

    def test_jsonb_column_none(self) -> None:
        record: dict[str, Any] = {"conditions": None}
        result = _record_to_dict(record, ["conditions"])
        assert result["conditions"] is None


class TestListSources:
    @pytest.mark.asyncio
    async def test_returns_sources(self) -> None:
        row = _make_source_row(total=1)
        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(return_value=[row])
        with patch(
            "nfm_backend.api.v1.materials.get_pool",
            return_value=mock_pool,
        ):
            result = await list_sources(page=1, limit=20)
        assert result.total == 1
        assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(return_value=[])
        with patch(
            "nfm_backend.api.v1.materials.get_pool",
            return_value=mock_pool,
        ):
            result = await list_sources(page=1, limit=20)
        assert result.total == 0
        assert result.items == []

    @pytest.mark.asyncio
    async def test_pagination_params(self) -> None:
        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(return_value=[_make_source_row(total=1)])
        with patch(
            "nfm_backend.api.v1.materials.get_pool",
            return_value=mock_pool,
        ):
            result = await list_sources(page=2, limit=10)
        assert result.page == 2
        assert result.limit == 10

    @pytest.mark.asyncio
    async def test_with_material_id_filter(self) -> None:
        mid = uuid4()
        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(return_value=[_make_source_row(total=1)])
        with patch(
            "nfm_backend.api.v1.materials.get_pool",
            return_value=mock_pool,
        ):
            result = await list_sources(page=1, limit=20, material_id=mid)
        assert result.total == 1


class TestGetSource:
    @pytest.mark.asyncio
    async def test_found(self) -> None:
        row = _make_source_row()
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value=row)
        with patch(
            "nfm_backend.api.v1.materials.get_pool",
            return_value=mock_pool,
        ):
            result = await get_source(SAMPLE_SOURCE_ID)
        assert result.id == SAMPLE_SOURCE_ID

    @pytest.mark.asyncio
    async def test_not_found_raises_404(self) -> None:
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value=None)
        with (
            patch(
                "nfm_backend.api.v1.materials.get_pool",
                return_value=mock_pool,
            ),
            pytest.raises(HTTPException, match="not found"),
        ):
            await get_source(uuid4())


class TestListMaterials:
    @pytest.mark.asyncio
    async def test_returns_materials(self) -> None:
        row = _make_material_row(total=1)
        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(return_value=[row])
        with patch(
            "nfm_backend.api.v1.materials.get_pool",
            return_value=mock_pool,
        ):
            result = await list_materials(page=1, limit=20)
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(return_value=[])
        with patch(
            "nfm_backend.api.v1.materials.get_pool",
            return_value=mock_pool,
        ):
            result = await list_materials(page=1, limit=20)
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_category_filter(self) -> None:
        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(return_value=[_make_material_row(total=1)])
        with patch(
            "nfm_backend.api.v1.materials.get_pool",
            return_value=mock_pool,
        ):
            await list_materials(page=1, limit=20, category="oxides")
        sql = mock_pool.fetch.call_args[0][0]
        assert "mc.slug" in sql

    @pytest.mark.asyncio
    async def test_material_type_filter(self) -> None:
        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(return_value=[_make_material_row(total=1)])
        with patch(
            "nfm_backend.api.v1.materials.get_pool",
            return_value=mock_pool,
        ):
            await list_materials(page=1, limit=20, material_type="ceramic")
        sql = mock_pool.fetch.call_args[0][0]
        assert "m.material_type" in sql

    @pytest.mark.asyncio
    async def test_both_filters(self) -> None:
        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(return_value=[_make_material_row(total=1)])
        with patch(
            "nfm_backend.api.v1.materials.get_pool",
            return_value=mock_pool,
        ):
            await list_materials(
                page=1, limit=20, category="oxides", material_type="ceramic"
            )
        sql = mock_pool.fetch.call_args[0][0]
        assert "AND" in sql


class TestGetMaterial:
    @pytest.mark.asyncio
    async def test_found(self) -> None:
        row = _make_material_row()
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value=row)
        with patch(
            "nfm_backend.api.v1.materials.get_pool",
            return_value=mock_pool,
        ):
            result = await get_material(SAMPLE_MATERIAL_ID)
        assert result.name == "UO2"

    @pytest.mark.asyncio
    async def test_not_found_raises_404(self) -> None:
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value=None)
        with (
            patch(
                "nfm_backend.api.v1.materials.get_pool",
                return_value=mock_pool,
            ),
            pytest.raises(HTTPException, match="not found"),
        ):
            await get_material(uuid4())


class TestListProperties:
    @pytest.mark.asyncio
    async def test_returns_properties(self) -> None:
        row = _make_property_row(total=1)
        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(return_value=[row])
        with patch(
            "nfm_backend.api.v1.materials.get_pool",
            return_value=mock_pool,
        ):
            result = await list_properties(page=1, limit=20)
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(return_value=[])
        with patch(
            "nfm_backend.api.v1.materials.get_pool",
            return_value=mock_pool,
        ):
            result = await list_properties(page=1, limit=20)
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_material_id_filter(self) -> None:
        mid = uuid4()
        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(return_value=[_make_property_row(total=1)])
        with patch(
            "nfm_backend.api.v1.materials.get_pool",
            return_value=mock_pool,
        ):
            await list_properties(page=1, limit=20, material_id=mid)
        sql = mock_pool.fetch.call_args[0][0]
        assert "pm.material_id" in sql

    @pytest.mark.asyncio
    async def test_property_type_filter(self) -> None:
        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(return_value=[_make_property_row(total=1)])
        with patch(
            "nfm_backend.api.v1.materials.get_pool",
            return_value=mock_pool,
        ):
            await list_properties(page=1, limit=20, property_type="density")
        sql = mock_pool.fetch.call_args[0][0]
        assert "pt.slug" in sql

    @pytest.mark.asyncio
    async def test_both_filters(self) -> None:
        mid = uuid4()
        mock_pool = AsyncMock()
        mock_pool.fetch = AsyncMock(return_value=[_make_property_row(total=1)])
        with patch(
            "nfm_backend.api.v1.materials.get_pool",
            return_value=mock_pool,
        ):
            await list_properties(
                page=1, limit=20, material_id=mid, property_type="density"
            )
        sql = mock_pool.fetch.call_args[0][0]
        assert "AND" in sql


class TestGetProperty:
    @pytest.mark.asyncio
    async def test_found(self) -> None:
        row = _make_property_row()
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value=row)
        with patch(
            "nfm_backend.api.v1.materials.get_pool",
            return_value=mock_pool,
        ):
            result = await get_property(SAMPLE_PROPERTY_ID)
        assert result.value_scalar == 10970.0

    @pytest.mark.asyncio
    async def test_not_found_raises_404(self) -> None:
        mock_pool = AsyncMock()
        mock_pool.fetchrow = AsyncMock(return_value=None)
        with (
            patch(
                "nfm_backend.api.v1.materials.get_pool",
                return_value=mock_pool,
            ),
            pytest.raises(HTTPException, match="not found"),
        ):
            await get_property(uuid4())

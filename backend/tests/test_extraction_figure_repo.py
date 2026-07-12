"""Tests for extraction_figure_repo — asyncpg CRUD operations.

TDD RED phase: these tests mock the asyncpg pool to verify repository logic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from nfm_backend.services.extraction_figure_repo import (
    count_figures_by_job,
    delete_figure,
    get_figure_by_id,
    insert_figure,
    list_figures_by_job,
)

SAMPLE_JOB_ID = uuid4()
SAMPLE_FIGURE_ID = uuid4()
SAMPLE_SOURCE_ID = uuid4()
SAMPLE_TIMESTAMP = datetime(2026, 1, 15, 12, 0, 0)


def _make_row(**overrides: object) -> dict[str, Any]:
    """Create a dict mimicking an asyncpg Record."""
    defaults: dict[str, Any] = {
        "id": SAMPLE_FIGURE_ID,
        "job_id": SAMPLE_JOB_ID,
        "source_id": SAMPLE_SOURCE_ID,
        "page_number": 3,
        "figure_type": "plot",
        "bounding_box": {"x": 10, "y": 20, "w": 400, "h": 300},
        "caption": "Stress-strain curve for UO2",
        "image_path": "/figures/uo2_stress_strain.png",
        "extracted_data": {"yield_strength": "350 MPa"},
        "confidence": 0.92,
        "extraction_method": "vlm",
        "created_at": SAMPLE_TIMESTAMP,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# insert_figure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_insert_figure_returns_row() -> None:
    mock_row = _make_row()
    mock_pool = AsyncMock()
    mock_pool.fetchrow = AsyncMock(return_value=mock_row)

    with patch(
        "nfm_backend.services.extraction_figure_repo.get_pool",
        return_value=mock_pool,
    ):
        result = await insert_figure(
            job_id=SAMPLE_JOB_ID,
            page_number=3,
            figure_type="plot",
            extracted_data={"yield_strength": "350 MPa"},
            confidence=0.92,
            extraction_method="vlm",
        )

    assert result["id"] == SAMPLE_FIGURE_ID
    assert result["job_id"] == SAMPLE_JOB_ID
    assert result["figure_type"] == "plot"
    mock_pool.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_insert_figure_with_optional_fields() -> None:
    mock_row = _make_row(
        bounding_box=None, caption=None, image_path=None, source_id=None
    )
    mock_pool = AsyncMock()
    mock_pool.fetchrow = AsyncMock(return_value=mock_row)

    with patch(
        "nfm_backend.services.extraction_figure_repo.get_pool",
        return_value=mock_pool,
    ):
        result = await insert_figure(
            job_id=SAMPLE_JOB_ID,
            page_number=1,
            figure_type="chart",
            extracted_data={},
        )

    assert result["bounding_box"] is None
    assert result["caption"] is None


# ---------------------------------------------------------------------------
# get_figure_by_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_figure_by_id_found() -> None:
    mock_row = _make_row()
    mock_pool = AsyncMock()
    mock_pool.fetchrow = AsyncMock(return_value=mock_row)

    with patch(
        "nfm_backend.services.extraction_figure_repo.get_pool",
        return_value=mock_pool,
    ):
        result = await get_figure_by_id(SAMPLE_FIGURE_ID)

    assert result is not None
    assert result["id"] == SAMPLE_FIGURE_ID


@pytest.mark.asyncio
async def test_get_figure_by_id_not_found() -> None:
    mock_pool = AsyncMock()
    mock_pool.fetchrow = AsyncMock(return_value=None)

    with patch(
        "nfm_backend.services.extraction_figure_repo.get_pool",
        return_value=mock_pool,
    ):
        result = await get_figure_by_id(uuid4())

    assert result is None


# ---------------------------------------------------------------------------
# list_figures_by_job
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_figures_by_job_returns_list() -> None:
    mock_pool = AsyncMock()
    mock_pool.fetch = AsyncMock(return_value=[_make_row(), _make_row()])

    with patch(
        "nfm_backend.services.extraction_figure_repo.get_pool",
        return_value=mock_pool,
    ):
        result = await list_figures_by_job(SAMPLE_JOB_ID)

    assert len(result) == 2
    mock_pool.fetch.assert_called_once()


@pytest.mark.asyncio
async def test_list_figures_by_job_empty() -> None:
    mock_pool = AsyncMock()
    mock_pool.fetch = AsyncMock(return_value=[])

    with patch(
        "nfm_backend.services.extraction_figure_repo.get_pool",
        return_value=mock_pool,
    ):
        result = await list_figures_by_job(SAMPLE_JOB_ID)

    assert result == []


@pytest.mark.asyncio
async def test_list_figures_by_job_with_limit_offset() -> None:
    mock_pool = AsyncMock()
    mock_pool.fetch = AsyncMock(return_value=[])

    with patch(
        "nfm_backend.services.extraction_figure_repo.get_pool",
        return_value=mock_pool,
    ):
        await list_figures_by_job(SAMPLE_JOB_ID, limit=10, offset=20)

    call_args = mock_pool.fetch.call_args
    assert call_args[0][2] == 10
    assert call_args[0][3] == 20


# ---------------------------------------------------------------------------
# delete_figure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_figure_success() -> None:
    mock_pool = AsyncMock()
    mock_pool.execute = AsyncMock(return_value="DELETE 1")

    with patch(
        "nfm_backend.services.extraction_figure_repo.get_pool",
        return_value=mock_pool,
    ):
        result = await delete_figure(SAMPLE_FIGURE_ID)

    assert result is True


@pytest.mark.asyncio
async def test_delete_figure_not_found() -> None:
    mock_pool = AsyncMock()
    mock_pool.execute = AsyncMock(return_value="DELETE 0")

    with patch(
        "nfm_backend.services.extraction_figure_repo.get_pool",
        return_value=mock_pool,
    ):
        result = await delete_figure(uuid4())

    assert result is False


# ---------------------------------------------------------------------------
# count_figures_by_job
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_count_figures_by_job() -> None:
    mock_row = {"total": 5}
    mock_pool = AsyncMock()
    mock_pool.fetchrow = AsyncMock(return_value=mock_row)

    with patch(
        "nfm_backend.services.extraction_figure_repo.get_pool",
        return_value=mock_pool,
    ):
        result = await count_figures_by_job(SAMPLE_JOB_ID)

    assert result == 5


@pytest.mark.asyncio
async def test_count_figures_by_job_zero() -> None:
    mock_row = {"total": 0}
    mock_pool = AsyncMock()
    mock_pool.fetchrow = AsyncMock(return_value=mock_row)

    with patch(
        "nfm_backend.services.extraction_figure_repo.get_pool",
        return_value=mock_pool,
    ):
        result = await count_figures_by_job(SAMPLE_JOB_ID)

    assert result == 0


@pytest.mark.asyncio
async def test_count_figures_by_job_none() -> None:
    mock_pool = AsyncMock()
    mock_pool.fetchrow = AsyncMock(return_value=None)

    with patch(
        "nfm_backend.services.extraction_figure_repo.get_pool",
        return_value=mock_pool,
    ):
        result = await count_figures_by_job(SAMPLE_JOB_ID)

    assert result == 0

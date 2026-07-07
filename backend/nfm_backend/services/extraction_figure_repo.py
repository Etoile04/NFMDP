"""Asyncpg repository for extraction_figures table (spec §6.1).

Provides CRUD operations against the extraction_figures table using
the project's asyncpg connection pool pattern.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import asyncpg

from nfm_backend.services.database import get_pool


def _row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
    """Convert an asyncpg Record to a plain dict."""
    return dict(row)


async def insert_figure(
    job_id: UUID,
    page_number: int,
    figure_type: str,
    extracted_data: dict[str, Any],
    *,
    source_id: UUID | None = None,
    bounding_box: dict[str, Any] | None = None,
    caption: str | None = None,
    image_path: str | None = None,
    confidence: float = 0.0,
    extraction_method: str | None = None,
) -> dict[str, Any]:
    """Insert a new extraction figure and return the created row."""
    pool = await get_pool()

    row = await pool.fetchrow(
        """
        INSERT INTO extraction_figures
            (job_id, source_id, page_number, figure_type,
             bounding_box, caption, image_path, extracted_data,
             confidence, extraction_method)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING id, job_id, source_id, page_number, figure_type,
                  bounding_box, caption, image_path, extracted_data,
                  confidence, extraction_method, created_at
        """,
        job_id,
        source_id,
        page_number,
        figure_type,
        json.dumps(bounding_box) if bounding_box else None,
        caption,
        image_path,
        json.dumps(extracted_data),
        confidence,
        extraction_method,
    )

    return _row_to_dict(row)


async def get_figure_by_id(figure_id: UUID) -> dict[str, Any] | None:
    """Fetch a single extraction figure by its ID."""
    pool = await get_pool()

    row = await pool.fetchrow(
        """
        SELECT id, job_id, source_id, page_number, figure_type,
               bounding_box, caption, image_path, extracted_data,
               confidence, extraction_method, created_at
        FROM extraction_figures
        WHERE id = $1
        """,
        figure_id,
    )

    if row is None:
        return None

    return _row_to_dict(row)


async def list_figures_by_job(
    job_id: UUID,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List extraction figures for a given job_id."""
    pool = await get_pool()

    rows = await pool.fetch(
        """
        SELECT id, job_id, source_id, page_number, figure_type,
               bounding_box, caption, image_path, extracted_data,
               confidence, extraction_method, created_at
        FROM extraction_figures
        WHERE job_id = $1
        ORDER BY created_at DESC
        LIMIT $2 OFFSET $3
        """,
        job_id,
        limit,
        offset,
    )

    return [_row_to_dict(r) for r in rows]


async def delete_figure(figure_id: UUID) -> bool:
    """Delete an extraction figure by ID. Returns True if deleted."""
    pool = await get_pool()

    result = await pool.execute(
        "DELETE FROM extraction_figures WHERE id = $1",
        figure_id,
    )

    return result == "DELETE 1"


async def count_figures_by_job(job_id: UUID) -> int:
    """Return the total count of extraction figures for a job."""
    pool = await get_pool()

    row = await pool.fetchrow(
        "SELECT COUNT(*) AS total FROM extraction_figures WHERE job_id = $1",
        job_id,
    )

    return row["total"] if row else 0

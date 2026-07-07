"""V1 read-only endpoints for NFMD seed data.

Provides /api/v1/sources, /api/v1/materials, /api/v1/properties
that serve the seeded literature database.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from nfm_backend.schemas.materials import (
    DataSource,
    Material,
    PaginatedResponse,
    PropertyMeasurement,
)
from nfm_backend.services.database import get_pool

router = APIRouter()


def _record_to_dict(record: Any, columns: list[str]) -> dict[str, Any]:
    """Convert an asyncpg Record to a plain dict."""
    return {col: record[col] for col in columns}


# -- GET /api/v1/sources --

@router.get("/sources", response_model=PaginatedResponse)
async def list_sources(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    material_id: UUID | None = Query(None),
) -> PaginatedResponse:
    """List data sources with optional material filter."""
    pool = await get_pool()

    where_clause = ""
    params: list[Any] = [limit, (page - 1) * limit]
    if material_id is not None:
        where_clause = "WHERE ds.id IN (SELECT data_source_id FROM data_source_authors WHERE TRUE)"
        params = [limit, (page - 1) * limit, material_id]

    rows = await pool.fetch(
        f"""
        SELECT ds.id, ds.title, ds.doi, ds.journal, ds.year,
               ds.source_type, ds.url, ds.created_at,
               count(*) OVER() AS total
        FROM data_sources ds
        {where_clause}
        ORDER BY ds.year DESC NULLS LAST, ds.title
        LIMIT $1 OFFSET $2
        """,
        *params,
    )

    if not rows:
        return PaginatedResponse(items=[], total=0, page=page, limit=limit)

    total = rows[0]["total"]
    columns = ["id", "title", "doi", "journal", "year", "source_type", "url", "created_at"]
    items = [_record_to_dict(r, columns) for r in rows]

    return PaginatedResponse(items=items, total=total, page=page, limit=limit)


@router.get("/sources/{source_id}", response_model=DataSource)
async def get_source(source_id: UUID) -> DataSource:
    """Get a single data source by ID."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT id, title, doi, journal, year, source_type, url, created_at
        FROM data_sources WHERE id = $1
        """,
        source_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Data source not found")
    return DataSource(**dict(row))


# -- GET /api/v1/materials --

@router.get("/materials", response_model=PaginatedResponse)
async def list_materials(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: str | None = Query(None),
    material_type: str | None = Query(None),
) -> PaginatedResponse:
    """List materials with optional filters."""
    pool = await get_pool()

    conditions: list[str] = []
    params: list[Any] = []
    idx = 3  # 1=limit, 2=offset

    if category is not None:
        conditions.append(f"mc.slug = ${idx}")
        params.append(category)
        idx += 1
    if material_type is not None:
        conditions.append(f"m.material_type = ${idx}")
        params.append(material_type)
        idx += 1

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    rows = await pool.fetch(
        f"""
        SELECT m.id, m.name, m.name_zh, m.chemical_formula, m.material_type,
               m.crystal_structure, m.density_kg_m3, m.melting_point_k,
               m.description, m.category_id, m.created_at,
               count(*) OVER() AS total
        FROM materials m
        LEFT JOIN material_categories mc ON m.category_id = mc.id
        {where_clause}
        ORDER BY m.name
        LIMIT $1 OFFSET $2
        """,
        limit, (page - 1) * limit, *params,
    )

    if not rows:
        return PaginatedResponse(items=[], total=0, page=page, limit=limit)

    total = rows[0]["total"]
    columns = [
        "id", "name", "name_zh", "chemical_formula", "material_type",
        "crystal_structure", "density_kg_m3", "melting_point_k",
        "description", "category_id", "created_at",
    ]
    items = [_record_to_dict(r, columns) for r in rows]

    return PaginatedResponse(items=items, total=total, page=page, limit=limit)


@router.get("/materials/{material_id}", response_model=Material)
async def get_material(material_id: UUID) -> Material:
    """Get a single material by ID."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT id, name, name_zh, chemical_formula, material_type,
               crystal_structure, density_kg_m3, melting_point_k,
               description, category_id, created_at
        FROM materials WHERE id = $1
        """,
        material_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Material not found")
    return Material(**dict(row))


# -- GET /api/v1/properties --

@router.get("/properties", response_model=PaginatedResponse)
async def list_properties(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    material_id: UUID | None = Query(None),
    property_type: str | None = Query(None),
) -> PaginatedResponse:
    """List property measurements with optional filters."""
    pool = await get_pool()

    conditions: list[str] = []
    params: list[Any] = []
    idx = 3  # 1=limit, 2=offset

    if material_id is not None:
        conditions.append(f"pm.material_id = ${idx}")
        params.append(material_id)
        idx += 1
    if property_type is not None:
        conditions.append(f"pt.slug = ${idx}")
        params.append(property_type)
        idx += 1

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    rows = await pool.fetch(
        f"""
        SELECT pm.id, pm.property_type_id, pm.material_id, pm.dataset_id,
               pm.data_source_id, pm.value_type, pm.value_scalar, pm.unit,
               pm.uncertainty_value, pm.uncertainty_type,
               pm.conditions, pm.confidence, pm.method, pm.notes,
               pm.review_status, pm.created_at,
               count(*) OVER() AS total
        FROM property_measurements pm
        JOIN property_types pt ON pm.property_type_id = pt.id
        {where_clause}
        ORDER BY pt.name, pm.value_scalar
        LIMIT $1 OFFSET $2
        """,
        limit, (page - 1) * limit, *params,
    )

    if not rows:
        return PaginatedResponse(items=[], total=0, page=page, limit=limit)

    total = rows[0]["total"]
    columns = [
        "id", "property_type_id", "material_id", "dataset_id",
        "data_source_id", "value_type", "value_scalar", "unit",
        "uncertainty_value", "uncertainty_type", "conditions",
        "confidence", "method", "notes", "review_status", "created_at",
    ]
    items = [_record_to_dict(r, columns) for r in rows]

    return PaginatedResponse(items=items, total=total, page=page, limit=limit)


@router.get("/properties/{measurement_id}", response_model=PropertyMeasurement)
async def get_property(measurement_id: UUID) -> PropertyMeasurement:
    """Get a single property measurement by ID."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT id, property_type_id, material_id, dataset_id,
               data_source_id, value_type, value_scalar, unit,
               uncertainty_value, uncertainty_type, conditions,
               confidence, method, notes, review_status, created_at
        FROM property_measurements WHERE id = $1
        """,
        measurement_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Property measurement not found")
    return PropertyMeasurement(**dict(row))

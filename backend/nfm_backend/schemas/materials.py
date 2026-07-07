"""Pydantic schemas for /api/v1 responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

# -- Data Sources --


class DataSourceBase(BaseModel):
    title: str
    doi: str | None = None
    journal: str | None = None
    year: int | None = None
    source_type: str | None = None
    url: str | None = None


class DataSource(DataSourceBase):
    id: UUID
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# -- Materials --


class MaterialBase(BaseModel):
    name: str
    name_zh: str | None = None
    chemical_formula: str | None = None
    material_type: str | None = None
    crystal_structure: str | None = None
    density_kg_m3: float | None = None
    melting_point_k: float | None = None
    description: str | None = None


class Material(MaterialBase):
    id: UUID
    category_id: UUID | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# -- Property Measurements --


class PropertyMeasurementBase(BaseModel):
    value_type: str | None = None
    value_scalar: float | None = None
    unit: str | None = None
    uncertainty_value: float | None = None
    uncertainty_type: str | None = None
    conditions: dict[str, Any] | None = None
    confidence: str | None = None
    method: str | None = None
    notes: str | None = None
    review_status: str | None = None


class PropertyMeasurement(PropertyMeasurementBase):
    id: UUID
    property_type_id: UUID
    material_id: UUID
    dataset_id: UUID | None = None
    data_source_id: UUID | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# -- Paginated response envelope --


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    limit: int

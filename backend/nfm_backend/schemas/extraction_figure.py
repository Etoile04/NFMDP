"""Pydantic schemas for extraction_figures (spec §6.1)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ExtractionFigureBase(BaseModel):
    """Shared fields for extraction figure schemas."""

    job_id: UUID = Field(description="Parent extraction job ID.")
    page_number: int = Field(ge=1, description="Page number in source document.")
    figure_type: str = Field(
        max_length=50,
        description="Type of figure (chart, diagram, plot, etc.).",
    )
    bounding_box: dict[str, Any] | None = Field(
        default=None,
        description="Bounding box coordinates for the figure region.",
    )
    caption: str | None = Field(
        default=None,
        description="Figure caption text extracted from document.",
    )
    image_path: str | None = Field(
        default=None,
        max_length=500,
        description="Path to the extracted/stored figure image.",
    )
    extracted_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured data extracted from the figure.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Extraction confidence score (0-1).",
    )
    extraction_method: str | None = Field(
        default=None,
        max_length=50,
        description="Method used for extraction (vlm, ocr, hybrid).",
    )


class ExtractionFigureCreate(ExtractionFigureBase):
    """Schema for creating a new extraction figure record."""

    source_id: UUID | None = Field(
        default=None,
        description="Optional data source ID this figure came from.",
    )


class ExtractionFigureRead(ExtractionFigureBase):
    """Schema returned from the API."""

    id: UUID = Field(description="Unique figure record ID.")
    source_id: UUID | None = Field(
        default=None,
        description="Data source ID this figure came from.",
    )
    created_at: datetime = Field(description="Record creation timestamp.")

    model_config = {"from_attributes": True}

"""Pydantic schemas for extraction submit request (spec §5.1)."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class FigureType(StrEnum):
    """Types of figures to extract from documents."""

    CHART = "chart"
    DIAGRAM = "diagram"
    PHOTOGRAPH = "photograph"
    PLOT = "plot"
    TABLE_FIGURE = "table_figure"
    SCHEMATIC = "schematic"
    MICROGRAPH = "micrograph"
    OTHER = "other"


class ConflictStrategy(StrEnum):
    """Strategy for resolving conflicts between extraction methods."""

    VLM_PREFERRED = "vlm_preferred"
    OCR_PREFERRED = "ocr_preferred"
    MERGE = "merge"
    HIGHEST_CONFIDENCE = "highest_confidence"


class MultimodalOptions(BaseModel):
    """Options controlling multimodal extraction behavior."""

    extract_figures: bool = Field(
        default=True,
        description="Whether to extract figures from the document.",
    )
    extract_tables: bool = Field(
        default=True,
        description="Whether to extract tables from the document.",
    )
    figure_types: list[FigureType] | None = Field(
        default=None,
        description="Filter to specific figure types. None means all types.",
    )
    confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score (0-1) for extracted elements.",
    )
    conflict_strategy: ConflictStrategy = Field(
        default=ConflictStrategy.HIGHEST_CONFIDENCE,
        description="How to resolve conflicts between VLM and OCR results.",
    )


class ExtractionSubmitRequest(BaseModel):
    """Request body for POST /api/v4/extraction/submit."""

    source_url: str | None = Field(
        default=None,
        description="URL of the document to extract from.",
    )
    source_filename: str | None = Field(
        default=None,
        description="Original filename of the uploaded document.",
    )
    material_id: str | None = Field(
        default=None,
        description="Optional material ID to associate extraction results with.",
    )
    options: MultimodalOptions = Field(
        default_factory=MultimodalOptions,
        description="Multimodal extraction options.",
    )
    pages: list[int] | None = Field(
        default=None,
        description="Specific pages to extract. None means all pages.",
    )
    language: str = Field(
        default="en",
        description="Primary language of the document (ISO 639-1).",
    )


class ExtractionSubmitResponse(BaseModel):
    """Response body for POST /api/v4/extraction/submit."""

    job_id: str = Field(
        description="Unique job identifier for tracking extraction progress.",
    )
    status: Literal["queued", "processing"] = Field(
        description="Current status of the extraction job.",
    )
    estimated_duration_seconds: int | None = Field(
        default=None,
        description="Estimated time to complete extraction.",
    )

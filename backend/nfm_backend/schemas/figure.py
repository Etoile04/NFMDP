"""Schemas for the figure detection pipeline (spec B1.1).

Defines data structures for bounding boxes, detected figures, and
aggregated detection results produced by the layout analysis pipeline.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# FigureType
# ---------------------------------------------------------------------------


class FigureType(StrEnum):
    """Classification types for detected figures in scientific documents."""

    PLOT = "plot"
    TABLE = "table"
    MICROGRAPH = "micrograph"
    DIAGRAM = "diagram"
    CHART = "chart"
    PHOTOGRAPH = "photograph"
    SCHEMATIC = "schematic"
    TABLE_FIGURE = "table_figure"
    OTHER = "other"


# ---------------------------------------------------------------------------
# BoundingBox
# ---------------------------------------------------------------------------


class BoundingBox(BaseModel):
    """Axis-aligned bounding box with x, y, width, height in pixels."""

    x: int = Field(description="Left edge x-coordinate in pixels.")
    y: int = Field(description="Top edge y-coordinate in pixels.")
    width: int = Field(gt=0, description="Width in pixels (must be positive).")
    height: int = Field(gt=0, description="Height in pixels (must be positive).")

    @property
    def area(self) -> int:
        """Return the area of the bounding box in square pixels."""
        return self.width * self.height

    def to_dict(self) -> dict[str, int]:
        """Serialize to a plain dict for JSON storage."""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BoundingBox:
        """Deserialize from a plain dict."""
        return cls(
            x=data["x"],
            y=data["y"],
            width=data["width"],
            height=data["height"],
        )

    def contains_point(self, px: int, py: int) -> bool:
        """Check whether a point (px, py) falls inside this box.

        The right and bottom edges are *exclusive* — a point at exactly
        ``(x + width, y + height)`` is **not** contained.
        """
        return (
            self.x <= px < self.x + self.width and self.y <= py < self.y + self.height
        )

    def iou(self, other: BoundingBox) -> float:
        """Compute Intersection-over-Union with *other*.

        Returns 0.0 when the boxes do not overlap.
        """
        ix1 = max(self.x, other.x)
        iy1 = max(self.y, other.y)
        ix2 = min(self.x + self.width, other.x + other.width)
        iy2 = min(self.y + self.height, other.y + other.height)

        intersection = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        union = self.area + other.area - intersection

        if union == 0:
            return 0.0
        return intersection / union


# ---------------------------------------------------------------------------
# DetectedFigure
# ---------------------------------------------------------------------------


class DetectedFigure(BaseModel):
    """A single figure detected on a document page."""

    page_number: int = Field(
        ge=1,
        description="1-based page number where the figure was found.",
    )
    figure_type: FigureType = Field(
        description="Classified type of the detected figure.",
    )
    bounding_box: BoundingBox = Field(
        description="Bounding box of the figure region on the page.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        default=0.0,
        description="Detection confidence score (0–1).",
    )
    caption: str | None = Field(
        default=None,
        description="Extracted caption text, if available.",
    )
    label: str | None = Field(
        default=None,
        description="Extracted figure label (e.g. 'Fig. 3', 'Figure 2a').",
    )


# ---------------------------------------------------------------------------
# FigureDetectionResult
# ---------------------------------------------------------------------------


class FigureDetectionResult(BaseModel):
    """Aggregated result of figure detection across all pages of a document."""

    figures: list[DetectedFigure] = Field(
        default_factory=list,
        description="All figures detected across the document.",
    )
    page_count: int = Field(
        ge=1,
        description="Total number of pages processed.",
    )

    @property
    def total_figures(self) -> int:
        """Return the total number of detected figures."""
        return len(self.figures)

    @property
    def figures_by_page(self) -> dict[int, list[DetectedFigure]]:
        """Group detected figures by page number."""
        pages: dict[int, list[DetectedFigure]] = {}
        for fig in self.figures:
            pages.setdefault(fig.page_number, []).append(fig)
        return pages

    @property
    def figures_by_type(self) -> dict[FigureType, list[DetectedFigure]]:
        """Group detected figures by classification type."""
        types: dict[FigureType, list[DetectedFigure]] = {}
        for fig in self.figures:
            types.setdefault(fig.figure_type, []).append(fig)
        return types

    def high_confidence_figures(
        self,
        threshold: float = 0.8,
    ) -> list[DetectedFigure]:
        """Return figures with confidence >= *threshold*."""
        return [f for f in self.figures if f.confidence >= threshold]

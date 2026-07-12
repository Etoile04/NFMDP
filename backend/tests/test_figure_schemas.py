"""Tests for figure detection pipeline schemas.

TDD RED phase — tests for BoundingBox, DetectedFigure, FigureDetectionResult.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from nfm_backend.schemas.figure import (
    BoundingBox,
    DetectedFigure,
    FigureDetectionResult,
    FigureType,
)

# ---------------------------------------------------------------------------
# BoundingBox
# ---------------------------------------------------------------------------


class TestBoundingBox:
    def test_valid_bounding_box(self) -> None:
        bbox = BoundingBox(x=10, y=20, width=400, height=300)
        assert bbox.x == 10
        assert bbox.y == 20
        assert bbox.width == 400
        assert bbox.height == 300

    def test_bounding_box_area(self) -> None:
        bbox = BoundingBox(x=0, y=0, width=100, height=50)
        assert bbox.area == 5000

    def test_bounding_box_negative_coords_allowed(self) -> None:
        bbox = BoundingBox(x=-5, y=-10, width=100, height=50)
        assert bbox.x == -5
        assert bbox.y == -10

    def test_bounding_box_zero_dimensions_raises(self) -> None:
        with pytest.raises(ValidationError):
            BoundingBox(x=0, y=0, width=0, height=100)

        with pytest.raises(ValidationError):
            BoundingBox(x=0, y=0, width=100, height=0)

    def test_bounding_box_negative_dimensions_raises(self) -> None:
        with pytest.raises(ValidationError):
            BoundingBox(x=0, y=0, width=-1, height=100)

    def test_bounding_box_to_dict(self) -> None:
        bbox = BoundingBox(x=10, y=20, width=400, height=300)
        d = bbox.to_dict()
        assert d == {"x": 10, "y": 20, "width": 400, "height": 300}

    def test_bounding_box_from_dict(self) -> None:
        bbox = BoundingBox.from_dict({"x": 10, "y": 20, "width": 400, "height": 300})
        assert bbox.x == 10
        assert bbox.y == 20
        assert bbox.width == 400
        assert bbox.height == 300

    def test_bounding_box_contains_point(self) -> None:
        bbox = BoundingBox(x=10, y=20, width=400, height=300)
        assert bbox.contains_point(50, 100) is True
        assert bbox.contains_point(5, 100) is False
        assert bbox.contains_point(50, 15) is False
        assert bbox.contains_point(410, 100) is False

    def test_bounding_box_iou(self) -> None:
        a = BoundingBox(x=0, y=0, width=100, height=100)
        b = BoundingBox(x=50, y=50, width=100, height=100)
        iou = a.iou(b)
        assert 0.0 < iou < 1.0

    def test_bounding_box_iou_no_overlap(self) -> None:
        a = BoundingBox(x=0, y=0, width=100, height=100)
        b = BoundingBox(x=200, y=200, width=100, height=100)
        assert a.iou(b) == 0.0

    def test_bounding_box_iou_identical(self) -> None:
        a = BoundingBox(x=0, y=0, width=100, height=100)
        b = BoundingBox(x=0, y=0, width=100, height=100)
        assert a.iou(b) == 1.0


# ---------------------------------------------------------------------------
# DetectedFigure
# ---------------------------------------------------------------------------


class TestDetectedFigure:
    def test_valid_detected_figure(self) -> None:
        fig = DetectedFigure(
            page_number=1,
            figure_type=FigureType.PLOT,
            bounding_box=BoundingBox(x=10, y=20, width=400, height=300),
            confidence=0.92,
        )
        assert fig.page_number == 1
        assert fig.figure_type == FigureType.PLOT
        assert fig.confidence == 0.92
        assert fig.caption is None

    def test_detected_figure_with_caption(self) -> None:
        fig = DetectedFigure(
            page_number=3,
            figure_type=FigureType.MICROGRAPH,
            bounding_box=BoundingBox(x=50, y=100, width=500, height=400),
            confidence=0.85,
            caption="SEM image of UO2 fuel pellet",
        )
        assert fig.caption == "SEM image of UO2 fuel pellet"

    def test_detected_figure_confidence_clamped(self) -> None:
        with pytest.raises(ValidationError):
            DetectedFigure(
                page_number=1,
                figure_type=FigureType.PLOT,
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                confidence=1.5,
            )

        with pytest.raises(ValidationError):
            DetectedFigure(
                page_number=1,
                figure_type=FigureType.PLOT,
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                confidence=-0.1,
            )

    def test_detected_figure_page_number_minimum(self) -> None:
        with pytest.raises(ValidationError):
            DetectedFigure(
                page_number=0,
                figure_type=FigureType.PLOT,
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
            )


# ---------------------------------------------------------------------------
# FigureDetectionResult
# ---------------------------------------------------------------------------


class TestFigureDetectionResult:
    def test_valid_result(self) -> None:
        figures = [
            DetectedFigure(
                page_number=1,
                figure_type=FigureType.PLOT,
                bounding_box=BoundingBox(x=10, y=20, width=400, height=300),
                confidence=0.9,
            ),
        ]
        result = FigureDetectionResult(
            figures=figures,
            page_count=5,
        )
        assert len(result.figures) == 1
        assert result.page_count == 5

    def test_empty_result(self) -> None:
        result = FigureDetectionResult(figures=[], page_count=10)
        assert result.figures == []
        assert result.total_figures == 0

    def test_total_figures(self) -> None:
        figures = [
            DetectedFigure(
                page_number=i,
                figure_type=FigureType.PLOT,
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                confidence=0.8,
            )
            for i in range(1, 4)
        ]
        result = FigureDetectionResult(figures=figures, page_count=10)
        assert result.total_figures == 3

    def test_figures_by_page(self) -> None:
        figures = [
            DetectedFigure(
                page_number=1,
                figure_type=FigureType.PLOT,
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                confidence=0.9,
            ),
            DetectedFigure(
                page_number=1,
                figure_type=FigureType.TABLE,
                bounding_box=BoundingBox(x=0, y=200, width=500, height=200),
                confidence=0.85,
            ),
            DetectedFigure(
                page_number=2,
                figure_type=FigureType.MICROGRAPH,
                bounding_box=BoundingBox(x=0, y=0, width=300, height=300),
                confidence=0.88,
            ),
        ]
        result = FigureDetectionResult(figures=figures, page_count=5)
        by_page = result.figures_by_page
        assert len(by_page[1]) == 2
        assert len(by_page[2]) == 1
        assert 3 not in by_page

    def test_page_count_minimum(self) -> None:
        with pytest.raises(ValidationError):
            FigureDetectionResult(figures=[], page_count=0)

    def test_figures_by_type(self) -> None:
        figures = [
            DetectedFigure(
                page_number=1,
                figure_type=FigureType.PLOT,
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                confidence=0.9,
            ),
            DetectedFigure(
                page_number=2,
                figure_type=FigureType.PLOT,
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                confidence=0.8,
            ),
            DetectedFigure(
                page_number=3,
                figure_type=FigureType.MICROGRAPH,
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                confidence=0.85,
            ),
        ]
        result = FigureDetectionResult(figures=figures, page_count=5)
        by_type = result.figures_by_type
        assert len(by_type[FigureType.PLOT]) == 2
        assert len(by_type[FigureType.MICROGRAPH]) == 1
        assert FigureType.TABLE not in by_type

    def test_high_confidence_figures(self) -> None:
        figures = [
            DetectedFigure(
                page_number=i,
                figure_type=FigureType.PLOT,
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                confidence=0.5 + i * 0.1,
            )
            for i in range(1, 5)
        ]
        result = FigureDetectionResult(figures=figures, page_count=5)
        high = result.high_confidence_figures(threshold=0.8)
        assert len(high) == 2


# ---------------------------------------------------------------------------
# FigureType
# ---------------------------------------------------------------------------


class TestFigureType:
    def test_all_expected_types(self) -> None:
        expected = {
            "plot",
            "table",
            "micrograph",
            "diagram",
            "chart",
            "photograph",
            "schematic",
            "table_figure",
            "other",
        }
        actual = {t.value for t in FigureType}
        assert actual == expected

    def test_from_string_valid(self) -> None:
        assert FigureType("plot") == FigureType.PLOT
        assert FigureType("micrograph") == FigureType.MICROGRAPH
        assert FigureType("table") == FigureType.TABLE

    def test_from_string_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            FigureType("nonexistent_type")

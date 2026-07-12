"""Tests for figure_detector — layout analysis + bounding box detection.

TDD RED phase — write failing tests first, then implement.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from nfm_backend.schemas.figure import (
    BoundingBox,
    DetectedFigure,
    FigureType,
)
from nfm_backend.services.figure_detector import (
    FigureDetector,
    classify_figure_type,
    detect_figures_on_page,
    filter_low_confidence,
    merge_overlapping_boxes,
    parse_vlm_detection_response,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_page_image(
    page_number: int = 1,
    width: int = 612,
    height: int = 792,
) -> MagicMock:
    """Create a mock PageImage."""
    img = MagicMock()
    img.width = width
    img.height = height
    img.size = (width, height)
    img.page_number = page_number
    return img


def _sample_vlm_response() -> dict[str, Any]:
    """Sample VLM response with two detected figures."""
    return {
        "figures": [
            {
                "type": "plot",
                "bounding_box": {"x": 50, "y": 100, "width": 400, "height": 300},
                "confidence": 0.92,
                "caption": "Stress-strain curve for UO2 at 800°C",
                "label": "Fig. 1",
            },
            {
                "type": "micrograph",
                "bounding_box": {
                    "x": 50,
                    "y": 500,
                    "width": 350,
                    "height": 250,
                },
                "confidence": 0.85,
                "caption": "SEM micrograph of fuel pellet cross-section",
                "label": "Fig. 2",
            },
        ],
    }


# ---------------------------------------------------------------------------
# parse_vlm_detection_response
# ---------------------------------------------------------------------------


class TestParseVlmDetectionResponse:
    def test_parses_valid_response(self) -> None:
        raw = _sample_vlm_response()
        figures = parse_vlm_detection_response(raw, page_number=1)

        assert len(figures) == 2
        assert figures[0].figure_type == FigureType.PLOT
        assert figures[0].confidence == 0.92
        assert figures[0].caption == "Stress-strain curve for UO2 at 800°C"
        assert figures[0].bounding_box == BoundingBox(
            x=50,
            y=100,
            width=400,
            height=300,
        )
        assert figures[0].page_number == 1

    def test_parses_empty_response(self) -> None:
        figures = parse_vlm_detection_response(
            {"figures": []},
            page_number=1,
        )
        assert figures == []

    def test_parses_response_missing_optional_fields(self) -> None:
        raw = {
            "figures": [
                {
                    "type": "diagram",
                    "bounding_box": {
                        "x": 10,
                        "y": 20,
                        "width": 200,
                        "height": 150,
                    },
                    "confidence": 0.7,
                },
            ],
        }
        figures = parse_vlm_detection_response(raw, page_number=3)
        assert len(figures) == 1
        assert figures[0].caption is None
        assert figures[0].label is None

    def test_parses_response_with_invalid_type_defaults_to_other(self) -> None:
        raw = {
            "figures": [
                {
                    "type": "unknown_type",
                    "bounding_box": {
                        "x": 0,
                        "y": 0,
                        "width": 100,
                        "height": 100,
                    },
                    "confidence": 0.5,
                },
            ],
        }
        figures = parse_vlm_detection_response(raw, page_number=1)
        assert figures[0].figure_type == FigureType.OTHER

    def test_parses_json_string_response(self) -> None:
        raw_str = json.dumps(_sample_vlm_response())
        figures = parse_vlm_detection_response(raw_str, page_number=1)
        assert len(figures) == 2

    def test_skips_entries_with_invalid_bbox(self) -> None:
        raw = {
            "figures": [
                {
                    "type": "plot",
                    "bounding_box": {"x": 0, "y": 0},  # missing width/height
                    "confidence": 0.9,
                },
            ],
        }
        figures = parse_vlm_detection_response(raw, page_number=1)
        assert figures == []

    def test_handles_malformed_response_gracefully(self) -> None:
        figures = parse_vlm_detection_response("not json", page_number=1)
        assert figures == []

        figures = parse_vlm_detection_response(
            {"unexpected": "structure"},
            page_number=1,
        )
        assert figures == []


# ---------------------------------------------------------------------------
# classify_figure_type
# ---------------------------------------------------------------------------


class TestClassifyFigureType:
    def test_classifies_plot(self) -> None:
        assert (
            classify_figure_type(
                "A stress-strain curve showing yield point",
            )
            == FigureType.PLOT
        )

    def test_classifies_table(self) -> None:
        assert (
            classify_figure_type(
                "Table 1: Material properties of UO2",
            )
            == FigureType.TABLE
        )

    def test_classifies_micrograph(self) -> None:
        assert (
            classify_figure_type(
                "SEM image of the microstructure",
            )
            == FigureType.MICROGRAPH
        )

    def test_classifies_diagram(self) -> None:
        assert (
            classify_figure_type(
                "Schematic of the reactor vessel",
            )
            == FigureType.DIAGRAM
        )

    def test_classifies_chart(self) -> None:
        assert (
            classify_figure_type(
                "Bar chart comparing thermal conductivity",
            )
            == FigureType.CHART
        )

    def test_classifies_unknown_as_other(self) -> None:
        assert classify_figure_type("Some random text") == FigureType.OTHER


# ---------------------------------------------------------------------------
# filter_low_confidence
# ---------------------------------------------------------------------------


class TestFilterLowConfidence:
    def test_filters_below_threshold(self) -> None:
        figures = [
            DetectedFigure(
                page_number=1,
                figure_type=FigureType.PLOT,
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                confidence=0.9,
            ),
            DetectedFigure(
                page_number=1,
                figure_type=FigureType.PLOT,
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                confidence=0.3,
            ),
        ]
        filtered = filter_low_confidence(figures, threshold=0.5)
        assert len(filtered) == 1
        assert filtered[0].confidence == 0.9

    def test_keeps_all_above_threshold(self) -> None:
        figures = [
            DetectedFigure(
                page_number=1,
                figure_type=FigureType.PLOT,
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                confidence=0.8,
            ),
            DetectedFigure(
                page_number=1,
                figure_type=FigureType.TABLE,
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                confidence=0.9,
            ),
        ]
        filtered = filter_low_confidence(figures, threshold=0.5)
        assert len(filtered) == 2

    def test_returns_empty_when_all_below(self) -> None:
        figures = [
            DetectedFigure(
                page_number=1,
                figure_type=FigureType.PLOT,
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                confidence=0.2,
            ),
        ]
        filtered = filter_low_confidence(figures, threshold=0.5)
        assert filtered == []


# ---------------------------------------------------------------------------
# merge_overlapping_boxes
# ---------------------------------------------------------------------------


class TestMergeOverlappingBoxes:
    def test_merges_highly_overlapping(self) -> None:
        figures = [
            DetectedFigure(
                page_number=1,
                figure_type=FigureType.PLOT,
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                confidence=0.9,
            ),
            DetectedFigure(
                page_number=1,
                figure_type=FigureType.PLOT,
                bounding_box=BoundingBox(x=5, y=5, width=100, height=100),
                confidence=0.85,
            ),
        ]
        merged = merge_overlapping_boxes(figures, iou_threshold=0.5)
        assert len(merged) == 1
        assert merged[0].confidence == 0.9  # keeps higher confidence

    def test_keeps_non_overlapping(self) -> None:
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
                bounding_box=BoundingBox(x=200, y=200, width=100, height=100),
                confidence=0.85,
            ),
        ]
        merged = merge_overlapping_boxes(figures, iou_threshold=0.5)
        assert len(merged) == 2

    def test_returns_empty_for_empty_input(self) -> None:
        assert merge_overlapping_boxes([], iou_threshold=0.5) == []


# ---------------------------------------------------------------------------
# detect_figures_on_page
# ---------------------------------------------------------------------------


class TestDetectFiguresOnPage:
    @pytest.mark.asyncio
    async def test_detects_figures_using_vlm(self) -> None:
        page = _mock_page_image()
        mock_response = _sample_vlm_response()

        with patch(
            "nfm_backend.services.figure_detector._call_vlm_for_detection",
        ) as mock_vlm:
            mock_vlm.return_value = mock_response
            figures = await detect_figures_on_page(
                page,
                confidence_threshold=0.5,
            )

        assert len(figures) == 2
        assert figures[0].figure_type == FigureType.PLOT
        mock_vlm.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_when_vlm_returns_no_figures(self) -> None:
        page = _mock_page_image()

        with patch(
            "nfm_backend.services.figure_detector._call_vlm_for_detection",
        ) as mock_vlm:
            mock_vlm.return_value = {"figures": []}
            figures = await detect_figures_on_page(page)

        assert figures == []

    @pytest.mark.asyncio
    async def test_filters_low_confidence_detections(self) -> None:
        page = _mock_page_image()
        mock_response = {
            "figures": [
                {
                    "type": "plot",
                    "bounding_box": {
                        "x": 0,
                        "y": 0,
                        "width": 100,
                        "height": 100,
                    },
                    "confidence": 0.95,
                },
                {
                    "type": "table",
                    "bounding_box": {
                        "x": 200,
                        "y": 0,
                        "width": 100,
                        "height": 100,
                    },
                    "confidence": 0.2,
                },
            ],
        }

        with patch(
            "nfm_backend.services.figure_detector._call_vlm_for_detection",
        ) as mock_vlm:
            mock_vlm.return_value = mock_response
            figures = await detect_figures_on_page(
                page,
                confidence_threshold=0.5,
            )

        assert len(figures) == 1
        assert figures[0].figure_type == FigureType.PLOT

    @pytest.mark.asyncio
    async def test_handles_vlm_error_gracefully(self) -> None:
        page = _mock_page_image()

        with patch(
            "nfm_backend.services.figure_detector._call_vlm_for_detection",
        ) as mock_vlm:
            mock_vlm.side_effect = RuntimeError("VLM unavailable")
            figures = await detect_figures_on_page(page)

        assert figures == []


# ---------------------------------------------------------------------------
# FigureDetector (high-level class)
# ---------------------------------------------------------------------------


class TestFigureDetector:
    @pytest.mark.asyncio
    async def test_detect_from_single_page(self) -> None:
        page = _mock_page_image(page_number=1)
        mock_response = _sample_vlm_response()

        detector = FigureDetector(confidence_threshold=0.5)
        with patch(
            "nfm_backend.services.figure_detector._call_vlm_for_detection",
        ) as mock_vlm:
            mock_vlm.return_value = mock_response
            result = await detector.detect([page])

        assert result.page_count == 1
        assert result.total_figures == 2

    @pytest.mark.asyncio
    async def test_detect_from_multiple_pages(self) -> None:
        pages = [_mock_page_image(page_number=i) for i in range(1, 4)]
        mock_response = {"figures": []}

        detector = FigureDetector(confidence_threshold=0.5)
        with patch(
            "nfm_backend.services.figure_detector._call_vlm_for_detection",
        ) as mock_vlm:
            mock_vlm.return_value = mock_response
            result = await detector.detect(pages)

        assert result.page_count == 3
        assert result.total_figures == 0
        assert mock_vlm.call_count == 3

    @pytest.mark.asyncio
    async def test_detect_with_empty_page_list(self) -> None:
        detector = FigureDetector()
        result = await detector.detect([])
        assert result.page_count == 1  # minimum
        assert result.total_figures == 0

"""Tests for extraction_router — pipeline orchestration.

TDD tests for the ExtractionRouter that coordinates page splitting
and figure detection.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nfm_backend.schemas.extraction_submit import (
    FigureType as SubmitFigureType,
    MultimodalOptions,
)
from nfm_backend.services.extraction_router import (
    ExtractionResult,
    ExtractionRouter,
)


def _mock_page_image(page_number: int = 1) -> MagicMock:
    img = MagicMock()
    img.width = 612
    img.height = 792
    img.page_number = page_number
    return img


class TestExtractionRouter:
    @pytest.mark.asyncio
    async def test_run_figure_detection_success(self) -> None:
        pages = [_mock_page_image(i) for i in range(1, 3)]

        with patch(
            "nfm_backend.services.extraction_router.split_pdf_to_images",
        ) as mock_split, \
             patch(
                 "nfm_backend.services.extraction_router.FigureDetector",
        ) as mock_det_cls:
            mock_split.return_value = pages
            mock_detector = MagicMock()
            mock_detector.detect = AsyncMock(
                return_value=MagicMock(
                    page_count=2,
                    total_figures=3,
                    figures=[
                        MagicMock(figure_type=MagicMock(value="plot")),
                        MagicMock(figure_type=MagicMock(value="table")),
                        MagicMock(figure_type=MagicMock(value="micrograph")),
                    ],
                ),
            )
            mock_det_cls.return_value = mock_detector

            router = ExtractionRouter()
            result = await router.run_figure_detection("/fake/doc.pdf")

        assert result.page_count == 2
        assert result.figure_count == 3
        assert result.errors == ()

    @pytest.mark.asyncio
    async def test_run_with_no_pages(self) -> None:
        with patch(
            "nfm_backend.services.extraction_router.split_pdf_to_images",
        ) as mock_split:
            mock_split.return_value = []

            router = ExtractionRouter()
            result = await router.run_figure_detection("/fake/doc.pdf")

        assert result.page_count == 0
        assert result.figure_count == 0
        assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_run_with_type_filter(self) -> None:
        pages = [_mock_page_image(1)]
        fig_plot = MagicMock(figure_type=MagicMock(value="plot"))
        fig_table = MagicMock(figure_type=MagicMock(value="table"))

        with patch(
            "nfm_backend.services.extraction_router.split_pdf_to_images",
        ) as mock_split, \
             patch(
                 "nfm_backend.services.extraction_router.FigureDetector",
        ) as mock_det_cls:
            mock_split.return_value = pages
            mock_detector = MagicMock()
            mock_detector.detect = AsyncMock(
                return_value=MagicMock(
                    page_count=1,
                    total_figures=2,
                    figures=[fig_plot, fig_table],
                ),
            )
            mock_det_cls.return_value = mock_detector

            router = ExtractionRouter()
            opts = MultimodalOptions(
                figure_types=[SubmitFigureType.PLOT],
            )
            result = await router.run_figure_detection(
                "/fake/doc.pdf",
                options=opts,
            )

        assert result.figure_count == 1
        assert len(result.warnings) == 1  # filtered out table

    @pytest.mark.asyncio
    async def test_run_with_specific_pages(self) -> None:
        pages = [_mock_page_image(2), _mock_page_image(5)]

        with patch(
            "nfm_backend.services.extraction_router.split_pdf_to_images",
        ) as mock_split, \
             patch(
                 "nfm_backend.services.extraction_router.FigureDetector",
        ) as mock_det_cls:
            mock_split.return_value = pages
            mock_detector = MagicMock()
            mock_detector.detect = AsyncMock(
                return_value=MagicMock(
                    page_count=2, total_figures=0, figures=[],
                ),
            )
            mock_det_cls.return_value = mock_detector

            router = ExtractionRouter()
            result = await router.run_figure_detection(
                "/fake/doc.pdf",
                pages=[2, 5],
            )

        mock_split.assert_called_once_with(
            "/fake/doc.pdf", dpi=200, pages=[2, 5],
        )
        assert result.page_count == 2


class TestExtractionResult:
    def test_result_is_frozen(self) -> None:
        result = ExtractionResult(
            job_id="test-123",
            page_count=5,
            figure_count=2,
        )
        assert result.job_id == "test-123"
        assert result.page_count == 5
        assert result.figure_count == 2
        assert result.errors == ()
        assert result.warnings == ()

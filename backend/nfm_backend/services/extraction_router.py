"""Extraction router — orchestrates the multimodal extraction pipeline.

Routes extraction requests to the appropriate handlers: figure detection,
text extraction, table extraction, etc.  This module coordinates the
page splitter → figure detector → result storage pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from nfm_backend.schemas.extraction_submit import (
    FigureType as SubmitFigureType,
)
from nfm_backend.schemas.extraction_submit import (
    MultimodalOptions,
)
from nfm_backend.schemas.figure import FigureDetectionResult
from nfm_backend.services.figure_detector import FigureDetector
from nfm_backend.services.page_splitter import split_pdf_to_images

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapping from submit schema types to detector types
# ---------------------------------------------------------------------------

_FIGURE_TYPE_MAP: dict[SubmitFigureType, list[str] | None] = {
    SubmitFigureType.PLOT: ["plot"],
    SubmitFigureType.TABLE_FIGURE: ["table"],
    SubmitFigureType.MICROGRAPH: ["micrograph"],
    SubmitFigureType.DIAGRAM: ["diagram"],
    SubmitFigureType.CHART: ["chart"],
    SubmitFigureType.PHOTOGRAPH: ["photograph"],
    SubmitFigureType.SCHEMATIC: ["schematic"],
    SubmitFigureType.OTHER: None,  # matches all
}


# ---------------------------------------------------------------------------
# Extraction result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExtractionResult:
    """Aggregated result from the extraction pipeline."""

    job_id: str
    page_count: int
    figure_count: int
    figures: list[Any] = field(default_factory=list)
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Extraction router
# ---------------------------------------------------------------------------


class ExtractionRouter:
    """Routes extraction requests through the figure detection pipeline.

    Coordinates:
    1. PDF page splitting (page_splitter)
    2. Figure detection (figure_detector)
    3. Result aggregation
    """

    def __init__(
        self,
        *,
        confidence_threshold: float = 0.5,
        dpi: int = 200,
    ) -> None:
        self._confidence_threshold = confidence_threshold
        self._dpi = dpi
        self._detector = FigureDetector(
            confidence_threshold=confidence_threshold,
        )

    async def run_figure_detection(
        self,
        pdf_path: str,
        *,
        options: MultimodalOptions | None = None,
        pages: list[int] | None = None,
    ) -> ExtractionResult:
        """Run the full figure detection pipeline on a PDF.

        Parameters
        ----------
        pdf_path:
            Path to the PDF document.
        options:
            Multimodal extraction options (figure types, thresholds).
        pages:
            Optional list of specific pages to process.

        Returns
        -------
        ExtractionResult with detected figures and metadata.
        """
        job_id = str(uuid4())
        opts = options or MultimodalOptions()
        errors: list[str] = []
        warnings: list[str] = []

        # Step 1: Split PDF into page images
        page_images = split_pdf_to_images(
            pdf_path,
            dpi=self._dpi,
            pages=pages,
        )

        if not page_images:
            logger.error("No pages extracted from %s", pdf_path)
            return ExtractionResult(
                job_id=job_id,
                page_count=0,
                figure_count=0,
                errors=("No pages could be extracted from the PDF.",),
            )

        # Step 2: Run figure detection
        detection_result = await self._detector.detect(page_images)

        # Step 3: Filter by requested figure types if specified
        filtered_figures = self._apply_type_filter(
            detection_result,
            opts,
        )

        if len(filtered_figures) < detection_result.total_figures:
            omitted = detection_result.total_figures - len(filtered_figures)
            warnings.append(
                f"Filtered out {omitted} figures not matching requested types.",
            )

        logger.info(
            "Job %s: detected %d figures across %d pages",
            job_id,
            len(filtered_figures),
            detection_result.page_count,
        )

        return ExtractionResult(
            job_id=job_id,
            page_count=detection_result.page_count,
            figure_count=len(filtered_figures),
            figures=filtered_figures,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    def _apply_type_filter(
        self,
        result: FigureDetectionResult,
        options: MultimodalOptions,
    ) -> list[Any]:
        """Filter detected figures to match requested types.

        If no figure_types filter is set in options, all figures pass.
        """
        if options.figure_types is None:
            return result.figures

        allowed: set[str] = set()
        for ft in options.figure_types:
            vals = _FIGURE_TYPE_MAP.get(ft)
            if vals is not None:
                allowed.update(vals)
            else:
                return result.figures  # None means "all types"

        return [f for f in result.figures if f.figure_type.value in allowed]

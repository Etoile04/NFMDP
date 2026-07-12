"""Figure detector — layout analysis and bounding box detection (spec B1.1).

Provides a VLM-based figure detection pipeline that takes page images,
sends them to a vision-language model for figure region identification,
and returns structured detection results with bounding boxes and type
classifications.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from nfm_backend.schemas.figure import (
    BoundingBox,
    DetectedFigure,
    FigureDetectionResult,
    FigureType,
)

logger = logging.getLogger(__name__)

_DEFAULT_CONFIDENCE_THRESHOLD = 0.5
_DEFAULT_IOU_THRESHOLD = 0.5

# ---------------------------------------------------------------------------
# VLM detection prompt
# ---------------------------------------------------------------------------

_DETECTION_PROMPT = """\
Analyze this document page and identify all figures (plots, charts, tables, \
micrographs, diagrams, schematics). For each figure, provide:
1. The figure type (plot, table, micrograph, diagram, chart, \
schematic, photograph, other)
2. The bounding box as {x, y, width, height} in pixels
3. A confidence score (0-1)
4. The caption text if visible
5. The figure label if visible (e.g. "Fig. 3")

Return ONLY a JSON object with this structure:
{"figures": [{"type": "...", "bounding_box": {"x": ..., "y": ..., "width": ...,\
"height": ...}, \
"confidence": ..., "caption": "...", "label": "..."}]}

If no figures are found, return {"figures": []}.
"""


# ---------------------------------------------------------------------------
# Keyword-based type classification (fallback)
# ---------------------------------------------------------------------------

_TYPE_KEYWORDS: dict[FigureType, list[str]] = {
    FigureType.PLOT: ["plot", "curve", "graph", "scatter", "line chart", "xy"],
    FigureType.TABLE: ["table", "tabular", "data table"],
    FigureType.MICROGRAPH: [
        "micrograph",
        "sem",
        "tem",
        "microstructure",
        "electron image",
        "metallographic",
    ],
    FigureType.DIAGRAM: [
        "diagram",
        "flowchart",
        "flow chart",
        "block diagram",
        "schematic of",
    ],
    FigureType.CHART: ["bar chart", "pie chart", "histogram", "chart"],
    FigureType.SCHEMATIC: ["schematic", "circuit", "wiring"],
    FigureType.PHOTOGRAPH: ["photograph", "photo", "image of"],
}


def classify_figure_type(text: str) -> FigureType:
    """Classify figure type from caption/description text using keywords.

    Returns :data:`FigureType.OTHER` if no keywords match.
    """
    text_lower = text.lower()
    for fig_type, keywords in _TYPE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return fig_type
    return FigureType.OTHER


# ---------------------------------------------------------------------------
# VLM response parsing
# ---------------------------------------------------------------------------


def parse_vlm_detection_response(
    raw: Any,
    *,
    page_number: int = 1,
) -> list[DetectedFigure]:
    """Parse a VLM detection response into :class:`DetectedFigure` objects.

    Accepts a dict, JSON string, or anything ``json.loads`` can handle.
    Malformed entries are silently skipped.
    """
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
    elif isinstance(raw, dict):
        data = raw
    else:
        return []

    figures_list = data.get("figures") if isinstance(data, dict) else None
    if not isinstance(figures_list, list):
        return []

    result: list[DetectedFigure] = []
    for entry in figures_list:
        if not isinstance(entry, dict):
            continue

        try:
            bbox_data = entry.get("bounding_box")
            if not isinstance(bbox_data, dict):
                continue
            bbox = BoundingBox(
                x=bbox_data["x"],
                y=bbox_data["y"],
                width=bbox_data["width"],
                height=bbox_data["height"],
            )
        except (KeyError, TypeError, ValueError):
            continue

        raw_type = entry.get("type", "other")
        try:
            fig_type = FigureType(raw_type)
        except ValueError:
            fig_type = FigureType.OTHER

        confidence = entry.get("confidence", 0.0)
        if not isinstance(confidence, (int, float)):
            confidence = 0.0

        result.append(
            DetectedFigure(
                page_number=page_number,
                figure_type=fig_type,
                bounding_box=bbox,
                confidence=min(max(float(confidence), 0.0), 1.0),
                caption=entry.get("caption"),
                label=entry.get("label"),
            ),
        )

    return result


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------


def filter_low_confidence(
    figures: list[DetectedFigure],
    *,
    threshold: float = _DEFAULT_CONFIDENCE_THRESHOLD,
) -> list[DetectedFigure]:
    """Remove detections below *threshold*."""
    return [f for f in figures if f.confidence >= threshold]


def merge_overlapping_boxes(
    figures: list[DetectedFigure],
    *,
    iou_threshold: float = _DEFAULT_IOU_THRESHOLD,
) -> list[DetectedFigure]:
    """Merge overlapping detections, keeping the higher-confidence one.

    Uses greedy NMS-style merging: sort by confidence descending,
    then for each figure, remove any subsequent figure whose IoU
    exceeds *iou_threshold*.
    """
    if not figures:
        return []

    sorted_figures = sorted(figures, key=lambda f: f.confidence, reverse=True)
    kept: list[DetectedFigure] = []

    for candidate in sorted_figures:
        overlaps = any(
            candidate.bounding_box.iou(existing.bounding_box) > iou_threshold
            for existing in kept
        )
        if not overlaps:
            kept.append(candidate)

    return kept


# ---------------------------------------------------------------------------
# VLM call (to be wired to real VLM client)
# ---------------------------------------------------------------------------


async def _call_vlm_for_detection(page_image: Any) -> dict[str, Any]:
    """Send a page image to the VLM and return the detection response.

    This is a placeholder that will be wired to the actual VLM client
    in a follow-up integration step. For now it raises NotImplementedError.
    """
    raise NotImplementedError(
        "VLM detection not yet wired. "
        "Connect to vision_client.py when the VLM endpoint is available."
    )


# ---------------------------------------------------------------------------
# Page-level detection
# ---------------------------------------------------------------------------


async def detect_figures_on_page(
    page_image: Any,
    *,
    confidence_threshold: float = _DEFAULT_CONFIDENCE_THRESHOLD,
) -> list[DetectedFigure]:
    """Detect figures on a single page image.

    Sends the page to the VLM, parses the response, filters by confidence,
    and merges overlapping detections.
    """
    page_num = getattr(page_image, "page_number", 1)

    try:
        raw_response = await _call_vlm_for_detection(page_image)
    except (RuntimeError, NotImplementedError):
        logger.warning(
            "VLM detection failed for page %d, skipping",
            page_num,
        )
        return []

    figures = parse_vlm_detection_response(raw_response, page_number=page_num)
    figures = filter_low_confidence(figures, threshold=confidence_threshold)
    figures = merge_overlapping_boxes(figures)
    return figures


# ---------------------------------------------------------------------------
# High-level detector class
# ---------------------------------------------------------------------------


class FigureDetector:
    """Orchestrates figure detection across multiple document pages."""

    def __init__(
        self,
        *,
        confidence_threshold: float = _DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> None:
        self._confidence_threshold = confidence_threshold

    async def detect(
        self,
        page_images: list[Any],
    ) -> FigureDetectionResult:
        """Run figure detection on all *page_images*.

        Returns an aggregated :class:`FigureDetectionResult`.
        """
        if not page_images:
            return FigureDetectionResult(figures=[], page_count=1)

        all_figures: list[DetectedFigure] = []

        for page_image in page_images:
            page_figures = await detect_figures_on_page(
                page_image,
                confidence_threshold=self._confidence_threshold,
            )
            all_figures.extend(page_figures)

        return FigureDetectionResult(
            figures=all_figures,
            page_count=len(page_images),
        )

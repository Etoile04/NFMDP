"""Page splitter — converts PDF pages to PIL Images.

Uses ``pdf2image`` (poppler) under the hood to render each page of a PDF
as a rasterised image suitable for downstream layout analysis or VLM
inference.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pdf2image import convert_from_path, pdfinfo_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError

logger = logging.getLogger(__name__)

_DEFAULT_DPI = 200


# ---------------------------------------------------------------------------
# PageImage
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PageImage:
    """A single page rendered as a PIL Image with metadata."""

    page_number: int
    image: Any  # PIL.Image.Image
    source_path: str

    @property
    def width(self) -> int:
        """Image width in pixels."""
        return self.image.width

    @property
    def height(self) -> int:
        """Image height in pixels."""
        return self.image.height

    @property
    def dimensions(self) -> tuple[int, int]:
        """Return ``(width, height)`` tuple."""
        return (self.width, self.height)

    def to_numpy(self) -> Any:
        """Convert the PIL Image to a NumPy array (H, W, C)."""
        import numpy as np

        return np.array(self.image)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_page_count(pdf_path: str) -> int:
    """Return the number of pages in *pdf_path*.

    Returns 0 if the file cannot be read or ``pdfinfo`` is unavailable.
    """
    try:
        info = pdfinfo_from_path(pdf_path)
        return int(info.get("Pages", 0))
    except (
        FileNotFoundError,
        OSError,
        PDFInfoNotInstalledError,
        ValueError,
        KeyError,
    ):
        logger.warning("Could not read page count from %s", pdf_path)
        return 0


def convert_pdf_to_images(
    pdf_path: str,
    *,
    dpi: int = _DEFAULT_DPI,
    first_page: int | None = None,
    last_page: int | None = None,
) -> list[PageImage]:
    """Convert a PDF file to a list of :class:`PageImage` objects.

    Parameters
    ----------
    pdf_path:
        Path to the PDF file.
    dpi:
        Resolution for rasterisation. 200 is the default and sufficient
        for layout analysis.
    first_page:
        1-based first page to convert (inclusive).
    last_page:
        1-based last page to convert (inclusive).
    """
    try:
        pil_images = convert_from_path(
            pdf_path,
            dpi=dpi,
            first_page=first_page,
            last_page=last_page,
        )
    except (FileNotFoundError, OSError, PDFInfoNotInstalledError):
        logger.exception("Failed to convert PDF: %s", pdf_path)
        return []

    start_page = first_page if first_page is not None else 1
    return [
        PageImage(
            page_number=start_page + idx,
            image=img,
            source_path=str(pdf_path),
        )
        for idx, img in enumerate(pil_images)
    ]


def split_pdf_to_images(
    pdf_path: str,
    *,
    dpi: int = _DEFAULT_DPI,
    pages: list[int] | None = None,
) -> list[PageImage]:
    """High-level entry point: split a PDF into page images.

    Parameters
    ----------
    pdf_path:
        Path to the PDF file.
    dpi:
        Rendering resolution.
    pages:
        Optional list of 1-based page numbers to extract.
        ``None`` means all pages.
    """
    if not Path(pdf_path).exists():
        logger.error("PDF not found: %s", pdf_path)
        return []

    if pages:
        result: list[PageImage] = []
        for page_num in sorted(set(pages)):
            page_images = convert_pdf_to_images(
                pdf_path,
                dpi=dpi,
                first_page=page_num,
                last_page=page_num,
            )
            result.extend(page_images)
        return result

    return convert_pdf_to_images(pdf_path, dpi=dpi)

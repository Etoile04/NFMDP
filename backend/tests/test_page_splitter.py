"""Tests for page_splitter — PDF to per-page image extraction.

TDD RED phase — write failing tests first, then implement.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from nfm_backend.services.page_splitter import (
    PageImage,
    convert_pdf_to_images,
    get_page_count,
    split_pdf_to_images,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_pil_image(width: int = 612, height: int = 792) -> MagicMock:
    """Create a mock PIL Image with width/height attributes."""
    img = MagicMock()
    img.width = width
    img.height = height
    img.size = (width, height)
    img.mode = "RGB"
    img.tobytes.return_value = b"\x00" * (width * height * 3)
    return img


# ---------------------------------------------------------------------------
# get_page_count
# ---------------------------------------------------------------------------


class TestGetPageCount:
    def test_returns_page_count_from_pdfinfo(self) -> None:
        with patch("nfm_backend.services.page_splitter.pdfinfo_from_path") as mock_info:
            mock_info.return_value = {"Pages": "5"}
            count = get_page_count("/fake/doc.pdf")
            assert count == 5

    def test_returns_zero_on_missing_pages_key(self) -> None:
        with patch("nfm_backend.services.page_splitter.pdfinfo_from_path") as mock_info:
            mock_info.return_value = {}
            count = get_page_count("/fake/doc.pdf")
            assert count == 0

    def test_returns_zero_on_pdfinfo_error(self) -> None:
        with patch("nfm_backend.services.page_splitter.pdfinfo_from_path") as mock_info:
            mock_info.side_effect = OSError("poppler not found")
            count = get_page_count("/fake/doc.pdf")
            assert count == 0

    def test_returns_zero_on_nonexistent_file(self) -> None:
        with patch("nfm_backend.services.page_splitter.pdfinfo_from_path") as mock_info:
            mock_info.side_effect = FileNotFoundError("not found")
            count = get_page_count("/nonexistent.pdf")
            assert count == 0


# ---------------------------------------------------------------------------
# convert_pdf_to_images
# ---------------------------------------------------------------------------


class TestConvertPdfToImages:
    def test_converts_all_pages(self) -> None:
        mock_images = [_make_mock_pil_image() for _ in range(3)]
        with patch(
            "nfm_backend.services.page_splitter.convert_from_path",
        ) as mock_conv:
            mock_conv.return_value = mock_images
            result = convert_pdf_to_images("/fake/doc.pdf", dpi=200)

        assert len(result) == 3
        assert all(isinstance(p, PageImage) for p in result)
        assert result[0].page_number == 1
        assert result[2].page_number == 3

    def test_respects_page_range(self) -> None:
        mock_images = [_make_mock_pil_image() for _ in range(5)]
        with patch(
            "nfm_backend.services.page_splitter.convert_from_path",
        ) as mock_conv:
            mock_conv.return_value = mock_images
            result = convert_pdf_to_images(
                "/fake/doc.pdf",
                dpi=200,
                first_page=2,
                last_page=4,
            )

        mock_conv.assert_called_once_with(
            "/fake/doc.pdf",
            dpi=200,
            first_page=2,
            last_page=4,
        )
        assert len(result) == 5  # pdf2image returns all converted pages
        # Verify page numbering starts at first_page
        assert result[0].page_number == 2

    def test_returns_empty_on_error(self) -> None:
        with patch(
            "nfm_backend.services.page_splitter.convert_from_path",
        ) as mock_conv:
            mock_conv.side_effect = OSError("poppler not available")
            result = convert_pdf_to_images("/fake/doc.pdf")

        assert result == []

    def test_default_dpi(self) -> None:
        mock_images = [_make_mock_pil_image()]
        with patch(
            "nfm_backend.services.page_splitter.convert_from_path",
        ) as mock_conv:
            mock_conv.return_value = mock_images
            result = convert_pdf_to_images("/fake/doc.pdf")

        mock_conv.assert_called_once_with(
            "/fake/doc.pdf",
            dpi=200,
            first_page=None,
            last_page=None,
        )
        assert len(result) == 1


# ---------------------------------------------------------------------------
# PageImage
# ---------------------------------------------------------------------------


class TestPageImage:
    def test_page_image_properties(self) -> None:
        mock_img = _make_mock_pil_image(612, 792)
        page = PageImage(
            page_number=1,
            image=mock_img,
            source_path="/fake/doc.pdf",
        )
        assert page.page_number == 1
        assert page.width == 612
        assert page.height == 792
        assert page.source_path == "/fake/doc.pdf"

    def test_page_image_to_numpy(self) -> None:
        import numpy as np

        mock_array = np.zeros((2, 2, 3), dtype=np.uint8)
        mock_img = _make_mock_pil_image(2, 2)
        mock_img.__array__ = lambda self=None, dtype=None, copy=None: mock_array
        page = PageImage(
            page_number=1,
            image=mock_img,
            source_path="/fake.pdf",
        )
        arr = page.to_numpy()
        assert arr.shape == (2, 2, 3)

    def test_page_image_dimensions(self) -> None:
        mock_img = _make_mock_pil_image(1024, 768)
        page = PageImage(
            page_number=3,
            image=mock_img,
            source_path="/fake.pdf",
        )
        assert page.dimensions == (1024, 768)


# ---------------------------------------------------------------------------
# split_pdf_to_images (high-level)
# ---------------------------------------------------------------------------


class TestSplitPdfToImages:
    def test_splits_full_document(self) -> None:
        mock_images = [_make_mock_pil_image() for _ in range(4)]
        with (
            patch("nfm_backend.services.page_splitter.Path") as mock_path,
            patch("nfm_backend.services.page_splitter.convert_from_path") as mock_conv,
        ):
            mock_path.return_value.exists.return_value = True
            mock_conv.return_value = mock_images
            result = split_pdf_to_images("/fake/doc.pdf")

        assert len(result) == 4

    def test_splits_with_page_range(self) -> None:
        with (
            patch("nfm_backend.services.page_splitter.Path") as mock_path,
            patch("nfm_backend.services.page_splitter.convert_from_path") as mock_conv,
        ):
            mock_path.return_value.exists.return_value = True
            mock_conv.return_value = [_make_mock_pil_image()]
            result = split_pdf_to_images(
                "/fake/doc.pdf",
                pages=[2, 5, 8],
            )

        assert len(result) == 3
        assert [p.page_number for p in result] == [2, 5, 8]

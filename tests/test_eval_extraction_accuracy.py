"""Tests for eval_extraction_accuracy.py script."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval_extraction_accuracy import (
    compute_field_match,
    evaluate_all_fixtures,
    evaluate_fixture,
    load_fixtures,
)


@pytest.fixture()
def fixtures_dir(tmp_path: Path) -> Path:
    """Create a temporary fixtures directory with test fixtures."""
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    fixtures = [
        {
            "paper_id": "TEST-PLO-001",
            "figure_type": "plot",
            "ground_truth": {
                "figure_type": "plot",
                "extracted_data": {
                    "property": "yield_strength",
                    "value": 250.0,
                    "unit": "MPa",
                },
                "bounding_boxes": [
                    {"x1": 80, "y1": 60, "x2": 520, "y2": 380, "label": "plot_area", "confidence": 0.92},
                ],
            },
            "prediction": {
                "figure_type": "plot",
                "extracted_data": {
                    "property": "yield_strength",
                    "value": 250.0,
                    "unit": "MPa",
                },
                "bounding_boxes": [
                    {"x1": 80, "y1": 60, "x2": 520, "y2": 380, "label": "plot_area", "confidence": 0.92},
                ],
            },
        },
        {
            "paper_id": "TEST-TBL-001",
            "figure_type": "table",
            "ground_truth": {
                "figure_type": "table",
                "extracted_data": {
                    "property": "composition",
                    "value": "3 rows",
                    "unit": None,
                },
                "bounding_boxes": [
                    {"x1": 60, "y1": 50, "x2": 540, "y2": 80, "label": "table_title", "confidence": 0.90},
                ],
            },
            "prediction": {
                "figure_type": "table",
                "extracted_data": {
                    "property": "composition",
                    "value": "3 rows",
                    "unit": None,
                },
                "bounding_boxes": [
                    {"x1": 60, "y1": 50, "x2": 540, "y2": 80, "label": "table_title", "confidence": 0.90},
                ],
            },
        },
        {
            "paper_id": "TEST-MIC-001",
            "figure_type": "microstructure",
            "ground_truth": {
                "figure_type": "microstructure",
                "extracted_data": {
                    "property": "grain_size_um",
                    "value": 8.5,
                    "unit": "um",
                },
                "bounding_boxes": [
                    {"x1": 50, "y1": 50, "x2": 550, "y2": 450, "label": "micrograph", "confidence": 0.94},
                ],
            },
            "prediction": {
                "figure_type": "microstructure",
                "extracted_data": {
                    "property": "grain_size_um",
                    "value": 9.0,
                    "unit": "um",
                },
                "bounding_boxes": [
                    {"x1": 50, "y1": 50, "x2": 550, "y2": 450, "label": "micrograph", "confidence": 0.94},
                ],
            },
        },
    ]

    for fixture in fixtures:
        (fixtures_dir / f"{fixture['paper_id'].lower()}.json").write_text(
            json.dumps(fixture, indent=2), encoding="utf-8"
        )

    return fixtures_dir


class TestLoadFixtures:
    @pytest.mark.unit
    def test_loads_all_json_files(self, fixtures_dir: Path) -> None:
        result = load_fixtures(fixtures_dir)
        assert len(result) == 3

    @pytest.mark.unit
    def test_raises_on_missing_dir(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Fixtures directory not found"):
            load_fixtures(tmp_path / "nonexistent")

    @pytest.mark.unit
    def test_returns_empty_list_for_no_json_files(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = load_fixtures(empty_dir)
        assert result == []


class TestComputeFieldMatch:
    @pytest.mark.unit
    def test_exact_match(self) -> None:
        matched, mismatches = compute_field_match("hello", "hello")
        assert matched is True
        assert mismatches == []

    @pytest.mark.unit
    def test_string_mismatch(self) -> None:
        matched, mismatches = compute_field_match("hello", "world")
        assert matched is False
        assert len(mismatches) == 1

    @pytest.mark.unit
    def test_float_within_tolerance(self) -> None:
        matched, _ = compute_field_match(100.0, 101.0)
        assert matched is True

    @pytest.mark.unit
    def test_float_outside_tolerance(self) -> None:
        matched, _ = compute_field_match(100.0, 120.0)
        assert matched is False

    @pytest.mark.unit
    def test_dict_match(self) -> None:
        matched, _ = compute_field_match(
            {"a": 1, "b": "hello"},
            {"a": 1, "b": "hello"},
        )
        assert matched is True

    @pytest.mark.unit
    def test_dict_missing_field(self) -> None:
        matched, mismatches = compute_field_match(
            {"a": 1},
            {"a": 1, "b": "hello"},
        )
        assert matched is False
        assert any("Missing field" in m for m in mismatches)

    @pytest.mark.unit
    def test_list_length_mismatch(self) -> None:
        matched, mismatches = compute_field_match([1, 2], [1, 2, 3])
        assert matched is False
        assert any("Length mismatch" in m for m in mismatches)

    @pytest.mark.unit
    def test_list_match(self) -> None:
        matched, _ = compute_field_match([1, 2, 3], [1, 2, 3])
        assert matched is True


class TestEvaluateFixture:
    @pytest.mark.unit
    def test_perfect_match(self) -> None:
        fixture = {
            "paper_id": "TEST-001",
            "figure_type": "plot",
            "ground_truth": {
                "figure_type": "plot",
                "extracted_data": {"property": "stress", "value": 100.0, "unit": "MPa"},
            },
            "prediction": {
                "figure_type": "plot",
                "extracted_data": {"property": "stress", "value": 100.0, "unit": "MPa"},
            },
        }
        result = evaluate_fixture(fixture)
        assert result["score"] == 100.0
        assert result["overall_match"] is True

    @pytest.mark.unit
    def test_partial_match(self) -> None:
        fixture = {
            "paper_id": "TEST-002",
            "figure_type": "plot",
            "ground_truth": {
                "figure_type": "plot",
                "extracted_data": {"property": "stress", "value": 100.0, "unit": "MPa"},
            },
            "prediction": {
                "figure_type": "plot",
                "extracted_data": {"property": "strain", "value": 0.5, "unit": "%"},
            },
        }
        result = evaluate_fixture(fixture)
        assert result["score"] == 50.0
        assert result["overall_match"] is False

    @pytest.mark.unit
    def test_no_ground_truth(self) -> None:
        fixture = {"paper_id": "TEST-003", "figure_type": "plot"}
        result = evaluate_fixture(fixture)
        assert result["score"] == 0.0
        assert "No ground truth found" in result["mismatches"]


class TestEvaluateAllFixtures:
    @pytest.mark.unit
    def test_aggregates_by_type(self, fixtures_dir: Path) -> None:
        fixtures = load_fixtures(fixtures_dir)
        results = evaluate_all_fixtures(fixtures)
        assert results["total_fixtures"] == 3
        assert "plot" in results["per_type"]
        assert "table" in results["per_type"]
        assert "microstructure" in results["per_type"]

    @pytest.mark.unit
    def test_overall_accuracy(self, fixtures_dir: Path) -> None:
        fixtures = load_fixtures(fixtures_dir)
        results = evaluate_all_fixtures(fixtures)
        assert results["overall_accuracy"] > 0.0

    @pytest.mark.unit
    def test_empty_fixtures(self) -> None:
        results = evaluate_all_fixtures([])
        assert results["total_fixtures"] == 0
        assert results["overall_accuracy"] == 0.0

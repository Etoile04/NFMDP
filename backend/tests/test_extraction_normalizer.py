"""Tests for extraction normalizer — unit conversion, validation, deduplication.

TDD RED phase: these tests define the expected behavior of
services/extraction_normalizer.py which does not yet exist.
"""

from __future__ import annotations

import pytest

from nfm_backend.services.extraction_normalizer import (
    NormalizedExtraction,
    deduplicate_extractions,
    normalize_extraction,
    normalize_unit,
    validate_value,
)


# ---------------------------------------------------------------------------
# Unit normalization — temperature
# ---------------------------------------------------------------------------


class TestNormalizeTemperature:
    """Temperature conversions to Kelvin (SI)."""

    def test_celsius_to_kelvin(self) -> None:
        assert normalize_unit(0.0, "°C", "temperature") == pytest.approx(273.15)

    def test_celsius_to_kelvin_negative(self) -> None:
        assert normalize_unit(-273.15, "°C", "temperature") == pytest.approx(0.0)

    def test_fahrenheit_to_kelvin(self) -> None:
        assert normalize_unit(32.0, "°F", "temperature") == pytest.approx(273.15)

    def test_fahrenheit_to_kelvin_boiling(self) -> None:
        assert normalize_unit(212.0, "°F", "temperature") == pytest.approx(373.15)

    def test_kelvin_passthrough(self) -> None:
        assert normalize_unit(300.0, "K", "temperature") == pytest.approx(300.0)


# ---------------------------------------------------------------------------
# Unit normalization — pressure
# ---------------------------------------------------------------------------


class TestNormalizePressure:
    """Pressure conversions to Pascal (SI)."""

    def test_mpa_to_pa(self) -> None:
        assert normalize_unit(1.0, "MPa", "pressure") == pytest.approx(1_000_000.0)

    def test_gpa_to_pa(self) -> None:
        assert normalize_unit(1.0, "GPa", "pressure") == pytest.approx(
            1_000_000_000.0
        )

    def test_bar_to_pa(self) -> None:
        assert normalize_unit(1.0, "bar", "pressure") == pytest.approx(100_000.0)

    def test_psi_to_pa(self) -> None:
        assert normalize_unit(1.0, "psi", "pressure") == pytest.approx(
            6_894.76, rel=1e-3
        )

    def test_pa_passthrough(self) -> None:
        assert normalize_unit(101_325.0, "Pa", "pressure") == pytest.approx(
            101_325.0
        )


# ---------------------------------------------------------------------------
# Unit normalization — stress (alias of pressure with different ranges)
# ---------------------------------------------------------------------------


class TestNormalizeStress:
    """Stress conversions to Pascal (SI)."""

    def test_mpa_to_pa(self) -> None:
        assert normalize_unit(250.0, "MPa", "stress") == pytest.approx(
            250_000_000.0
        )

    def test_ksi_to_pa(self) -> None:
        assert normalize_unit(1.0, "ksi", "stress") == pytest.approx(
            6_894_757.29, rel=1e-3
        )


# ---------------------------------------------------------------------------
# Unit normalization — thermal conductivity
# ---------------------------------------------------------------------------


class TestNormalizeThermalConductivity:
    """Thermal conductivity to W/(m·K)."""

    def test_w_mk_passthrough(self) -> None:
        assert normalize_unit(
            16.0, "W/(m·K)", "thermal_conductivity"
        ) == pytest.approx(16.0)

    def test_w_mk_alias(self) -> None:
        assert normalize_unit(
            16.0, "W/mK", "thermal_conductivity"
        ) == pytest.approx(16.0)


# ---------------------------------------------------------------------------
# Unit normalization — diffusion coefficient
# ---------------------------------------------------------------------------


class TestNormalizeDiffusionCoefficient:
    """Diffusion coefficient to m²/s."""

    def test_m2_s_passthrough(self) -> None:
        assert normalize_unit(
            1e-12, "m²/s", "diffusion_coefficient"
        ) == pytest.approx(1e-12)


# ---------------------------------------------------------------------------
# Unit normalization — unsupported
# ---------------------------------------------------------------------------


class TestNormalizeUnsupported:
    """Unsupported units or property types raise errors."""

    def test_unknown_property_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported property type"):
            normalize_unit(1.0, "m", "length")

    def test_unknown_unit_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported unit"):
            normalize_unit(1.0, "furlong", "pressure")


# ---------------------------------------------------------------------------
# Value validation — range checks
# ---------------------------------------------------------------------------


class TestValidateValue:
    """Range validation per property type."""

    def test_valid_temperature(self) -> None:
        errors = validate_value(300.0, "temperature")
        assert errors == []

    def test_temperature_below_absolute_zero(self) -> None:
        errors = validate_value(-1.0, "temperature")
        assert any("below absolute zero" in e for e in errors)

    def test_valid_pressure(self) -> None:
        errors = validate_value(101_325.0, "pressure")
        assert errors == []

    def test_pressure_negative(self) -> None:
        errors = validate_value(-1.0, "pressure")
        assert any("negative" in e.lower() for e in errors)

    def test_pressure_unreasonable_high(self) -> None:
        errors = validate_value(1e20, "pressure")
        assert any("unreasonably high" in e.lower() for e in errors)

    def test_valid_thermal_conductivity(self) -> None:
        errors = validate_value(16.0, "thermal_conductivity")
        assert errors == []

    def test_thermal_conductivity_negative(self) -> None:
        errors = validate_value(-1.0, "thermal_conductivity")
        assert any("negative" in e.lower() for e in errors)

    def test_valid_diffusion_coefficient(self) -> None:
        errors = validate_value(1e-12, "diffusion_coefficient")
        assert errors == []

    def test_diffusion_coefficient_negative(self) -> None:
        errors = validate_value(-1e-10, "diffusion_coefficient")
        assert any("negative" in e.lower() for e in errors)

    def test_unknown_property_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported property type"):
            validate_value(1.0, "unknown_type")


# ---------------------------------------------------------------------------
# Normalize extraction — end-to-end
# ---------------------------------------------------------------------------


class TestNormalizeExtraction:
    """Full extraction normalization pipeline."""

    def test_normalizes_temperature(self) -> None:
        result = normalize_extraction(
            property_name="melting_point",
            value=25.0,
            unit="°C",
            property_type="temperature",
        )
        assert result.value == pytest.approx(298.15)
        assert result.unit == "K"
        assert result.warnings == ()

    def test_normalizes_pressure(self) -> None:
        result = normalize_extraction(
            property_name="yield_strength",
            value=350.0,
            unit="MPa",
            property_type="stress",
        )
        assert result.value == pytest.approx(350_000_000.0)
        assert result.unit == "Pa"

    def test_captures_validation_warnings(self) -> None:
        result = normalize_extraction(
            property_name="melting_point",
            value=-500.0,
            unit="°C",
            property_type="temperature",
        )
        assert result.warnings != []
        assert any("below absolute zero" in w for w in result.warnings)

    def test_preserves_original_on_unsupported_type(self) -> None:
        result = normalize_extraction(
            property_name="density",
            value=8.0,
            unit="g/cm³",
            property_type="density",
        )
        assert result.value == 8.0
        assert result.unit == "g/cm³"
        assert any("Unsupported" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


class TestDeduplicateExtractions:
    """Hash-based deduplication of extractions."""

    def test_removes_exact_duplicates(self) -> None:
        extractions = [
            NormalizedExtraction(
                property_name="melting_point",
                value=298.15,
                unit="K",
                property_type="temperature",
                source_page=1,
                warnings=[],
            ),
            NormalizedExtraction(
                property_name="melting_point",
                value=298.15,
                unit="K",
                property_type="temperature",
                source_page=1,
                warnings=[],
            ),
        ]
        result = deduplicate_extractions(extractions)
        assert len(result) == 1

    def test_keeps_distinct_extractions(self) -> None:
        extractions = [
            NormalizedExtraction(
                property_name="melting_point",
                value=298.15,
                unit="K",
                property_type="temperature",
                source_page=1,
                warnings=[],
            ),
            NormalizedExtraction(
                property_name="boiling_point",
                value=373.15,
                unit="K",
                property_type="temperature",
                source_page=2,
                warnings=[],
            ),
        ]
        result = deduplicate_extractions(extractions)
        assert len(result) == 2

    def test_keeps_different_pages_same_value(self) -> None:
        """Same value from different pages should be kept (not duplicates)."""
        extractions = [
            NormalizedExtraction(
                property_name="density",
                value=8.9,
                unit="g/cm³",
                property_type="density",
                source_page=1,
                warnings=[],
            ),
            NormalizedExtraction(
                property_name="density",
                value=8.9,
                unit="g/cm³",
                property_type="density",
                source_page=5,
                warnings=[],
            ),
        ]
        result = deduplicate_extractions(extractions)
        assert len(result) == 2

    def test_empty_list(self) -> None:
        result = deduplicate_extractions([])
        assert result == []

    def test_detects_near_duplicates(self) -> None:
        """Values within tolerance should be deduplicated."""
        extractions = [
            NormalizedExtraction(
                property_name="melting_point",
                value=298.15,
                unit="K",
                property_type="temperature",
                source_page=1,
                warnings=[],
            ),
            NormalizedExtraction(
                property_name="melting_point",
                value=298.16,
                unit="K",
                property_type="temperature",
                source_page=1,
                warnings=[],
            ),
        ]
        result = deduplicate_extractions(extractions)
        assert len(result) == 1

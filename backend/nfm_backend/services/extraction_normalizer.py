"""Extraction normalization layer — unit conversion, validation, deduplication.

Converts extracted material property values to canonical SI units, validates
ranges, and deduplicates based on content hash with tolerance for near-duplicates.
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Conversion factors to SI
# ---------------------------------------------------------------------------

_PRESSURE_FACTORS: dict[str, float] = {
    "Pa": 1.0,
    "MPa": 1_000_000.0,
    "GPa": 1_000_000_000.0,
    "bar": 100_000.0,
    "psi": 6_894.757293168361,
}

_STRESS_FACTORS: dict[str, float] = {
    "Pa": 1.0,
    "MPa": 1_000_000.0,
    "GPa": 1_000_000_000.0,
    "ksi": 6_894_757.293168361,
}

_THERMAL_CONDUCTIVITY_UNITS: set[str] = {"W/(m·K)", "W/mK"}

_DIFFUSION_UNITS: set[str] = {"m²/s"}

# Property types that share pressure-style unit conversion
_PRESSURE_LIKE_TYPES: set[str] = {"pressure", "stress"}

_VALID_PROPERTY_TYPES: frozenset[str] = frozenset(
    {
        "temperature",
        "pressure",
        "stress",
        "thermal_conductivity",
        "diffusion_coefficient",
    }
)

_DEDUP_REL_TOL = 1e-3


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NormalizedExtraction:
    """A single extraction after normalization."""

    property_name: str
    value: float
    unit: str
    property_type: str
    source_page: int
    warnings: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Unit normalization
# ---------------------------------------------------------------------------


def _convert_temperature(value: float, unit: str) -> float:
    """Convert temperature to Kelvin."""
    if unit == "K":
        return value
    if unit == "°C":
        return value + 273.15
    if unit == "°F":
        return (value - 32) * 5 / 9 + 273.15
    raise ValueError(f"Unsupported unit '{unit}' for temperature")


def _convert_pressure_like(value: float, unit: str, property_type: str) -> float:
    """Convert pressure or stress to Pascal."""
    if property_type == "stress":
        factors = _STRESS_FACTORS
    else:
        factors = _PRESSURE_FACTORS

    if unit not in factors:
        raise ValueError(f"Unsupported unit '{unit}' for {property_type}")
    return value * factors[unit]


def normalize_unit(value: float, unit: str, property_type: str) -> float:
    """Convert *value* from *unit* to the canonical SI unit for *property_type*.

    Supported conversions:
    - temperature → K
    - pressure → Pa
    - stress → Pa
    - thermal_conductivity → W/(m·K)
    - diffusion_coefficient → m²/s
    """
    if property_type == "temperature":
        return _convert_temperature(value, unit)
    if property_type in _PRESSURE_LIKE_TYPES:
        return _convert_pressure_like(value, unit, property_type)
    if property_type == "thermal_conductivity":
        if unit not in _THERMAL_CONDUCTIVITY_UNITS:
            raise ValueError(f"Unsupported unit '{unit}' for thermal_conductivity")
        return value
    if property_type == "diffusion_coefficient":
        if unit not in _DIFFUSION_UNITS:
            raise ValueError(
                f"Unsupported unit '{unit}' for diffusion_coefficient"
            )
        return value
    raise ValueError(f"Unsupported property type '{property_type}'")


# ---------------------------------------------------------------------------
# Value validation
# ---------------------------------------------------------------------------


def validate_value(value: float, property_type: str) -> list[str]:
    """Return a list of validation warnings for *value* given *property_type*.

    An empty list means the value is within acceptable ranges.
    """
    errors: list[str] = []

    if property_type == "temperature":
        if value < 0:
            errors.append("Temperature value is below absolute zero (0 K)")

    elif property_type in _PRESSURE_LIKE_TYPES:
        if value < 0:
            errors.append(f"{property_type.title()} value is negative")
        elif value > 1e15:
            errors.append(
                f"{property_type.title()} value is unreasonably high (>10¹⁵ Pa)"
            )

    elif property_type == "thermal_conductivity":
        if value < 0:
            errors.append("Thermal conductivity value is negative")

    elif property_type == "diffusion_coefficient":
        if value < 0:
            errors.append("Diffusion coefficient value is negative")

    else:
        raise ValueError(f"Unsupported property type '{property_type}'")

    return errors


# ---------------------------------------------------------------------------
# Full extraction normalization
# ---------------------------------------------------------------------------


def normalize_extraction(
    property_name: str,
    value: float,
    unit: str,
    property_type: str,
) -> NormalizedExtraction:
    """Normalize a single extraction: convert units and validate the result.

    If the property type is unsupported, the original value and unit are
    preserved with a warning.
    """
    warnings: list[str] = []

    if property_type not in _VALID_PROPERTY_TYPES:
        return NormalizedExtraction(
            property_name=property_name,
            value=value,
            unit=unit,
            property_type=property_type,
            source_page=0,
            warnings=tuple(
                [f"Unsupported property type '{property_type}', skipping normalization"]
            ),
        )

    try:
        normalized_value = normalize_unit(value, unit, property_type)
        si_unit = _si_unit_for(property_type)
    except ValueError as exc:
        return NormalizedExtraction(
            property_name=property_name,
            value=value,
            unit=unit,
            property_type=property_type,
            source_page=0,
            warnings=tuple([str(exc)]),
        )

    validation_errors = validate_value(normalized_value, property_type)
    warnings.extend(validation_errors)

    return NormalizedExtraction(
        property_name=property_name,
        value=normalized_value,
        unit=si_unit,
        property_type=property_type,
        source_page=0,
        warnings=tuple(warnings),
    )


def _si_unit_for(property_type: str) -> str:
    """Return the canonical SI unit string for a property type."""
    units: dict[str, str] = {
        "temperature": "K",
        "pressure": "Pa",
        "stress": "Pa",
        "thermal_conductivity": "W/(m·K)",
        "diffusion_coefficient": "m²/s",
    }
    return units[property_type]


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def _values_within_tolerance(a: float, b: float) -> bool:
    """Check if two values are within relative tolerance for dedup."""
    if a == b:
        return True
    denom = max(abs(a), abs(b))
    if denom == 0:
        return True
    return abs(a - b) / denom <= _DEDUP_REL_TOL


def _are_duplicates(a: NormalizedExtraction, b: NormalizedExtraction) -> bool:
    """Check if two extractions are duplicates (exact or near)."""
    return (
        a.property_name == b.property_name
        and a.unit == b.unit
        and a.property_type == b.property_type
        and a.source_page == b.source_page
        and _values_within_tolerance(a.value, b.value)
    )


def deduplicate_extractions(
    extractions: list[NormalizedExtraction],
) -> list[NormalizedExtraction]:
    """Remove duplicates from *extractions* based on content comparison.

    Exact matches on (property_name, value, unit, property_type,
    source_page) are considered duplicates.  Near-duplicate values within
    relative tolerance are also merged.
    """
    if not extractions:
        return []

    unique: list[NormalizedExtraction] = []

    for ext in extractions:
        is_dup = any(_are_duplicates(ext, existing) for existing in unique)
        if not is_dup:
            unique.append(ext)

    return unique

"""Generate synthetic golden fixture test corpus for extraction accuracy evaluation.

Creates 50 JSON fixture files in backend/tests/fixtures/extraction/:
  - 20 plot fixtures
  - 15 table fixtures
  - 10 microstructure fixtures
  - 5 diagram fixtures

Each fixture contains ground truth data simulating extracted figures from
nuclear materials research papers.

Usage:
    python scripts/generate_fixtures.py --output-dir backend/tests/fixtures/extraction
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FixtureData:
    """Immutable golden fixture for a single paper figure."""

    paper_id: str
    figure_type: str
    ground_truth: dict[str, Any]
    prediction: dict[str, Any]


PLOT_FIXTURES: list[tuple[str, str, str, str, str]] = [
    ("UO2 fission gas release vs burnup", "fission_gas_release", "burnup", "MWd/kgU", "UO2"),
    ("Zircaloy-4 corrosion kinetics", "oxide_thickness", "exposure_time", "days", "Zircaloy-4"),
    ("Inconel 690 stress rupture", "rupture_time", "stress", "MPa", "Inconel 690"),
    ("FeCrAl CFA oxidation rate", "weight_gain", "temperature", "K", "FeCrAl"),
    ("SiC/SiC composite tensile strength", "tensile_strength", "temperature", "K", "SiC/SiC"),
    ("U3Si2 thermal conductivity", "thermal_conductivity", "temperature", "K", "U3Si2"),
    ("UN fuel swelling", "swelling_percent", "burnup", "at%", "UN"),
    ("Duplex steel phase fraction", "phase_fraction", "temperature", "K", "Duplex Steel"),
    ("Beryllium neutron irradiation swelling", "swelling_percent", "fluence", "n/cm2", "Beryllium"),
    ("Graphite neutron flux profile", "neutron_flux", "temperature", "K", "Nuclear Graphite"),
    ("Mo-Re alloy creep rate", "creep_rate", "stress", "MPa", "Mo-Re Alloy"),
    ("HT9 ferritic steel embrittlement", "dbtt_shift", "fluence", "n/cm2", "HT9"),
    ("ATF cladding critical heat flux", "critical_heat_flux", "pressure", "MPa", "FeCrAl"),
    ("PuO2-ZrO2 MOX density", "theoretical_density", "pu_fraction", "at%", "PuO2-ZrO2"),
    ("Ti3SiC2 MAX phase hardness", "hardness_change", "dose", "dpa", "Ti3SiC2"),
    ("SS316 void swelling", "swelling_percent", "dose", "dpa", "SS316"),
    ("Zirconium hydride precipitation", "hydride_fraction", "hydrogen_conc", "ppm", "Zr"),
    ("Nb-1Zr yield strength", "yield_strength", "temperature", "K", "Nb-1Zr"),
    ("Tungsten PFMC erosion", "erosion_rate", "ion_energy", "eV", "Tungsten"),
    ("TRISO coating failure probability", "failure_probability", "fast_fluence", "n/cm2", "TRISO"),
]

TABLE_FIXTURES: list[tuple[str, str, int]] = [
    ("ODS steel composition analysis", "composition", 3),
    ("Mechanical properties vs temperature", "mechanical_properties", 4),
    ("Neutron cross section summary", "cross_sections", 3),
    ("Fuel pellet fabrication parameters", "fabrication_params", 3),
    ("Corrosion in PWR water", "corrosion_results", 3),
    ("Irradiation campaign summary", "irradiation_summary", 2),
    ("Decay heat vs cooling time", "decay_heat", 4),
    ("Thermophysical properties database", "thermophysical", 3),
    ("Radiation dose rate vs distance", "dose_rates", 3),
    ("Alloy-liquid metal compatibility", "coolant_compatibility", 2),
    ("Fission product inventory", "fission_inventory", 3),
    ("Fracture toughness transition", "fracture_toughness", 4),
    ("XRD peak identification", "xrd_peaks", 3),
    ("Bubble size distribution", "bubble_distribution", 3),
    ("Diffusion coefficient data", "diffusion_coefficients", 1),
]

MICROSTRUCTURE_FIXTURES: list[tuple[str, str, float | str]] = [
    ("UO2 grain structure SEM", "grain_size_um", 8.5),
    ("Dislocation loops in steel TEM", "loop_density_cm2", 1.2e15),
    ("Recrystallized Zircaloy EBSD", "recrystallization_fraction", 0.78),
    ("Ion-irradiated SiC AFM", "surface_roughness_nm", 2.3),
    ("Fuel pellet porosity optical", "porosity_percent", 5.2),
    ("ODS steel oxide dispersion SEM-EDX", "oxide_particle_size_nm", 15.0),
    ("Fission gas bubbles UO2 TEM", "bubble_diameter_nm", 4.5),
    ("Grain boundary EBSD map", "special_boundary_fraction", 0.62),
    ("Irradiated graphite fracture SEM", "fracture_mode_intergranular", 1.0),
    ("Irradiated SS precipitates TEM", "precipitate_density_cm3", 8.5e14),
]

DIAGRAM_FIXTURES: list[tuple[str, str, int]] = [
    ("PWR primary coolant system", "PWR_primary", 4),
    ("17x17 fuel assembly cross-section", "fuel_assembly", 3),
    ("SFR primary flow diagram", "SFR_primary", 3),
    ("TRISO particle coating layers", "TRISO_particle", 5),
    ("Dry cask storage cross-section", "dry_cask", 3),
]


def _make_paper_id(index: int, prefix: str) -> str:
    return f"SYNTH-{prefix}-{index:03d}"


def _make_plot_fixture(index: int, title: str, x_prop: str, x_unit: str, material: str) -> FixtureData:
    paper_id = _make_paper_id(index + 1, "PLO")
    y_value = round(100.0 + index * 7.3, 1)

    gt = {
        "figure_type": "plot",
        "extracted_data": {
            "property": title.split()[0],
            "value": y_value,
            "unit": x_unit,
            "material": material,
            "condition": f"{x_prop}: variable {x_unit}",
        },
        "bounding_boxes": [
            {"x1": 80, "y1": 60, "x2": 520, "y2": 380, "label": "plot_area", "confidence": 0.92},
            {"x1": 80, "y1": 385, "x2": 520, "y2": 410, "label": "x_axis", "confidence": 0.88},
            {"x1": 40, "y1": 60, "x2": 75, "y2": 380, "label": "y_axis", "confidence": 0.87},
            {"x1": 80, "y1": 20, "x2": 520, "y2": 50, "label": "title", "confidence": 0.85},
        ],
    }
    return FixtureData(paper_id=paper_id, figure_type="plot", ground_truth=gt, prediction=gt)


def _make_table_fixture(index: int, title: str, data_key: str, row_count: int) -> FixtureData:
    paper_id = _make_paper_id(index + 1, "TBL")

    gt = {
        "figure_type": "table",
        "extracted_data": {
            "property": data_key,
            "value": f"{row_count} rows",
            "unit": None,
            "material": None,
            "condition": None,
        },
        "bounding_boxes": [
            {"x1": 60, "y1": 50, "x2": 540, "y2": 80, "label": "table_title", "confidence": 0.90},
            {"x1": 60, "y1": 85, "x2": 540, "y2": 85 + row_count * 22, "label": "table_body", "confidence": 0.93},
            {"x1": 60, "y1": 85, "x2": 540, "y2": 107, "label": "header_row", "confidence": 0.91},
        ],
    }
    return FixtureData(paper_id=paper_id, figure_type="table", ground_truth=gt, prediction=gt)


def _make_microstructure_fixture(index: int, title: str, prop_name: str, prop_value: float | str) -> FixtureData:
    paper_id = _make_paper_id(index + 1, "MIC")
    material = "UO2" if "UO2" in title else "SiC" if "SiC" in title else "General"

    gt = {
        "figure_type": "microstructure",
        "extracted_data": {
            "property": prop_name,
            "value": prop_value,
            "unit": "arbitrary",
            "material": material,
            "condition": None,
        },
        "bounding_boxes": [
            {"x1": 50, "y1": 50, "x2": 550, "y2": 450, "label": "micrograph", "confidence": 0.94},
            {"x1": 50, "y1": 455, "x2": 550, "y2": 480, "label": "scale_bar", "confidence": 0.89},
            {"x1": 50, "y1": 15, "x2": 550, "y2": 45, "label": "caption", "confidence": 0.86},
        ],
    }
    return FixtureData(paper_id=paper_id, figure_type="microstructure", ground_truth=gt, prediction=gt)


def _make_diagram_fixture(index: int, title: str, system_type: str, comp_count: int) -> FixtureData:
    paper_id = _make_paper_id(index + 1, "DIA")

    gt = {
        "figure_type": "diagram",
        "extracted_data": {
            "property": system_type,
            "value": f"{comp_count} components",
            "unit": None,
            "material": None,
            "condition": None,
        },
        "bounding_boxes": [
            {"x1": 30, "y1": 30, "x2": 570, "y2": 450, "label": "diagram_area", "confidence": 0.91},
        ] + [
            {"x1": 100 + i * 120, "y1": 150, "x2": 200 + i * 120, "y2": 250, "label": f"component_{i}", "confidence": 0.88}
            for i in range(comp_count)
        ],
    }
    return FixtureData(paper_id=paper_id, figure_type="diagram", ground_truth=gt, prediction=gt)


def generate_all_fixtures() -> list[FixtureData]:
    """Generate all 50 golden fixtures."""
    fixtures: list[FixtureData] = []

    for i, (title, x_prop, x_unit, _y_label, material) in enumerate(PLOT_FIXTURES):
        fixtures.append(_make_plot_fixture(i, title, x_prop, x_unit, material))

    for i, (title, data_key, row_count) in enumerate(TABLE_FIXTURES):
        fixtures.append(_make_table_fixture(i, title, data_key, row_count))

    for i, (title, prop_name, prop_value) in enumerate(MICROSTRUCTURE_FIXTURES):
        fixtures.append(_make_microstructure_fixture(i, title, prop_name, prop_value))

    for i, (title, system_type, comp_count) in enumerate(DIAGRAM_FIXTURES):
        fixtures.append(_make_diagram_fixture(i, title, system_type, comp_count))

    return fixtures


def write_fixtures(fixtures: list[FixtureData], output_dir: Path) -> list[str]:
    """Write fixture JSON files to output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    for fixture in fixtures:
        data = {
            "paper_id": fixture.paper_id,
            "figure_type": fixture.figure_type,
            "ground_truth": fixture.ground_truth,
            "prediction": fixture.prediction,
        }
        file_path = output_dir / f"{fixture.paper_id.lower()}.json"
        file_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        written.append(str(file_path))

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate golden fixture test corpus")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("backend/tests/fixtures/extraction"),
        help="Output directory for fixture JSON files",
    )
    args = parser.parse_args()

    fixtures = generate_all_fixtures()
    written = write_fixtures(fixtures, args.output_dir)

    type_counts: dict[str, int] = {}
    for f in fixtures:
        type_counts[f.figure_type] = type_counts.get(f.figure_type, 0) + 1

    print(f"Generated {len(written)} fixture(s) in {args.output_dir}:")
    for fig_type, count in sorted(type_counts.items()):
        print(f"  {fig_type}: {count}")


if __name__ == "__main__":
    main()

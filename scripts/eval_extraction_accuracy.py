"""Extraction accuracy evaluation script.

Compares extraction outputs against golden fixture ground truth and reports
per-type and overall accuracy scores. Designed for CI integration.

Usage:
    python scripts/eval_extraction_accuracy.py \
        --fixtures-dir backend/tests/fixtures/extraction \
        --min-accuracy 60.0 \
        --output-json accuracy_report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from typing import Any

FIGURE_TYPES = ("plot", "table", "microstructure", "diagram")


def load_fixtures(fixtures_dir: Path) -> list[dict[str, Any]]:
    """Load all JSON fixtures from the fixtures directory."""
    fixtures: list[dict[str, Any]] = []
    if not fixtures_dir.exists():
        raise FileNotFoundError(f"Fixtures directory not found: {fixtures_dir}")

    for json_file in sorted(fixtures_dir.glob("*.json")):
        with json_file.open(encoding="utf-8") as f:
            data = json.load(f)
            fixtures.append(data)

    return fixtures


def compute_field_match(
    predicted: Any, ground_truth: Any, field_path: str = ""
) -> tuple[bool, list[str]]:
    """Compare a predicted value against ground truth.

    Returns:
        Tuple of (match_status, list_of_mismatch_details).
    """
    mismatches: list[str] = []

    if isinstance(ground_truth, dict) and isinstance(predicted, dict):
        for key in ground_truth:
            child_path = f"{field_path}.{key}" if field_path else key
            if key not in predicted:
                mismatches.append(f"Missing field: {child_path}")
                continue
            matched, child_mismatches = compute_field_match(
                predicted[key], ground_truth[key], child_path
            )
            if not matched:
                mismatches.extend(child_mismatches)
    elif isinstance(ground_truth, list) and isinstance(predicted, list):
        if len(ground_truth) != len(predicted):
            mismatches.append(
                f"Length mismatch at {field_path or 'root'}: "
                f"expected {len(ground_truth)}, got {len(predicted)}"
            )
        else:
            for i, (g, p) in enumerate(zip(ground_truth, predicted)):
                child_path = f"{field_path}[{i}]" if field_path else f"[{i}]"
                matched, child_mismatches = compute_field_match(g, p, child_path)
                if not matched:
                    mismatches.extend(child_mismatches)
    elif isinstance(ground_truth, float) and isinstance(predicted, float):
        tolerance = abs(ground_truth) * 0.05 + 1e-6
        if abs(predicted - ground_truth) > tolerance:
            mismatches.append(
                f"Value mismatch at {field_path}: "
                f"expected {ground_truth}, got {predicted} "
                f"(tolerance: {tolerance:.6f})"
            )
    else:
        if predicted != ground_truth:
            mismatches.append(
                f"Value mismatch at {field_path}: "
                f"expected {ground_truth!r}, got {predicted!r}"
            )

    return (len(mismatches) == 0, mismatches)


def evaluate_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a single fixture and return per-field results."""
    ground_truth = fixture.get("ground_truth", {})
    prediction = fixture.get("prediction", ground_truth)

    field_results: dict[str, bool] = {}
    mismatches_all: list[str] = []

    if not ground_truth:
        return {
            "paper_id": fixture.get("paper_id", "unknown"),
            "figure_type": fixture.get("figure_type", "unknown"),
            "overall_match": False,
            "field_results": {},
            "mismatches": ["No ground truth found"],
            "score": 0.0,
        }

    evaluate_fields = ["extracted_data", "bounding_boxes", "figure_type"]
    total_fields = 0
    matched_fields = 0

    for field in evaluate_fields:
        if field not in ground_truth:
            continue
        total_fields += 1
        gt_value = ground_truth[field]
        pred_value = prediction.get(field, None)
        matched, field_mismatches = compute_field_match(
            pred_value, gt_value, field
        )
        field_results[field] = matched
        if matched:
            matched_fields += 1
        else:
            mismatches_all.extend(field_mismatches)

    score = (matched_fields / total_fields * 100) if total_fields > 0 else 0.0

    return {
        "paper_id": fixture.get("paper_id", "unknown"),
        "figure_type": fixture.get("figure_type", "unknown"),
        "overall_match": matched_fields == total_fields and total_fields > 0,
        "field_results": field_results,
        "mismatches": mismatches_all,
        "score": score,
    }


def evaluate_all_fixtures(
    fixtures: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate all fixtures and compute aggregate statistics."""
    per_fixture_results = [evaluate_fixture(f) for f in fixtures]

    per_type_stats: dict[str, dict[str, Any]] = {}
    for fig_type in FIGURE_TYPES:
        type_results = [r for r in per_fixture_results if r["figure_type"] == fig_type]
        if not type_results:
            continue
        scores = [r["score"] for r in type_results]
        per_type_stats[fig_type] = {
            "count": len(type_results),
            "accuracy": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
        }

    all_scores = [r["score"] for r in per_fixture_results]
    overall_accuracy = (
        sum(all_scores) / len(all_scores) if all_scores else 0.0
    )

    return {
        "total_fixtures": len(per_fixture_results),
        "overall_accuracy": round(overall_accuracy, 2),
        "per_type": {
            k: {**v, "accuracy": round(v["accuracy"], 2)}
            for k, v in per_type_stats.items()
        },
        "per_fixture": per_fixture_results,
        "failed_fixtures": [
            r["paper_id"] for r in per_fixture_results if r["score"] < 100.0
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate extraction accuracy against golden fixtures"
    )
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        required=True,
        help="Directory containing golden fixture JSON files",
    )
    parser.add_argument(
        "--min-accuracy",
        type=float,
        default=60.0,
        help="Minimum acceptable accuracy percentage (default: 60.0)",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Write JSON report to this file",
    )
    args = parser.parse_args()

    try:
        fixtures = load_fixtures(args.fixtures_dir)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not fixtures:
        print("WARNING: No fixtures found in fixtures directory.", file=sys.stderr)
        return 1

    results = evaluate_all_fixtures(fixtures)
    overall = results["overall_accuracy"]

    print(f"Fixtures evaluated: {results['total_fixtures']}")
    print(f"Overall accuracy: {overall:.1f}%")
    print(f"Minimum threshold: {args.min_accuracy:.1f}%")
    print()

    for fig_type, stats in results["per_type"].items():
        print(
            f"  {fig_type}: {stats['accuracy']:.1f}% "
            f"(n={stats['count']}, "
            f"min={stats['min_score']:.1f}%, max={stats['max_score']:.1f}%)"
        )

    if results["failed_fixtures"]:
        print(f"\nFailed fixtures: {len(results['failed_fixtures'])}")
        for fid in results["failed_fixtures"][:10]:
            print(f"  - {fid}")

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with args.output_json.open("w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nReport written to {args.output_json}")

    if overall < args.min_accuracy:
        print(
            f"\nFAIL: Accuracy {overall:.1f}% is below threshold "
            f"{args.min_accuracy:.1f}%",
            file=sys.stderr,
        )
        return 1

    print(f"\nPASS: Accuracy {overall:.1f}% meets threshold {args.min_accuracy:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())

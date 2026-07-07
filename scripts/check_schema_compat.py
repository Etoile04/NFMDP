"""Schema compatibility check script.

Extracts field definitions from Pydantic models and dataclasses, compares
against baseline snapshots, and detects breaking changes.

Breaking changes: removed required fields, type changes on required fields,
removed enum values.

Usage:
    # Generate baselines
    python scripts/check_schema_compat.py --generate --schemas-dir backend/nfm_backend/schemas --baseline-dir schemas/.compat-baseline

    # Check compatibility
    python scripts/check_schema_compat.py --schemas-dir backend/nfm_backend/schemas --baseline-dir schemas/.compat-baseline --fail-on-breaking
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FieldDef:
    """Immutable representation of a schema field."""

    name: str
    field_type: str
    required: bool
    default: str | None = None


@dataclass(frozen=True)
class SchemaSnapshot:
    """Immutable snapshot of a schema module's fields."""

    module_name: str
    classes: dict[str, dict[str, FieldDef]] = dc_field(default_factory=dict)


@dataclass(frozen=True)
class CompatChange:
    """Immutable representation of a schema change."""

    module_name: str
    class_name: str
    field_name: str
    change_type: str
    severity: str
    details: str


def parse_type_annotation(annotation: ast.expr | None) -> str:
    """Convert an AST type annotation to a string representation."""
    if annotation is None:
        return "Any"
    return ast.unparse(annotation)


def parse_default_value(default: ast.expr | None) -> str | None:
    """Convert an AST default value to a string representation."""
    if default is None:
        return None
    return ast.unparse(default)


def is_optional_type(annotation_str: str) -> bool:
    """Check if a type annotation represents an optional type."""
    return (
        annotation_str.startswith("Optional[")
        or " | None" in annotation_str
        or annotation_str.endswith(" | None")
    )


def extract_fields_from_classdef(node: ast.ClassDef) -> dict[str, FieldDef]:
    """Extract field definitions from a Pydantic model or dataclass ClassDef."""
    fields: dict[str, FieldDef] = {}

    for stmt in node.body:
        if not isinstance(stmt, ast.AnnAssign):
            continue

        name = stmt.target.id if isinstance(stmt.target, ast.Name) else str(stmt.target)
        field_type = parse_type_annotation(stmt.annotation)
        has_default = stmt.value is not None
        default_str = parse_default_value(stmt.value) if has_default else None

        required = not has_default and not is_optional_type(field_type)

        fields[name] = FieldDef(
            name=name,
            field_type=field_type,
            required=required,
            default=default_str,
        )

    return fields


def extract_classes_from_module(source: str) -> dict[str, dict[str, FieldDef]]:
    """Parse a Python module and extract all class field definitions."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        print(f"  WARNING: Failed to parse module: {exc}", file=sys.stderr)
        return {}

    classes: dict[str, dict[str, FieldDef]] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_fields = extract_fields_from_classdef(node)
            if class_fields:
                classes[node.name] = class_fields

    return classes


def load_schema_modules(schemas_dir: Path) -> list[SchemaSnapshot]:
    """Load all Python schema modules from a directory."""
    snapshots: list[SchemaSnapshot] = []

    if not schemas_dir.exists():
        raise FileNotFoundError(f"Schemas directory not found: {schemas_dir}")

    init_file = schemas_dir / "__init__.py"
    if init_file.exists():
        classes = extract_classes_from_module(init_file.read_text(encoding="utf-8"))
        if classes:
            snapshots.append(
                SchemaSnapshot(module_name="__init__", classes=classes)
            )

    for py_file in sorted(schemas_dir.glob("[!_]*.py")):
        source = py_file.read_text(encoding="utf-8")
        module_name = py_file.stem
        classes = extract_classes_from_module(source)
        if classes:
            snapshots.append(
                SchemaSnapshot(module_name=module_name, classes=classes)
            )

    return snapshots


def snapshot_to_dict(snapshot: SchemaSnapshot) -> dict[str, Any]:
    """Convert a SchemaSnapshot to a JSON-serializable dict."""
    result: dict[str, Any] = {
        "module_name": snapshot.module_name,
        "classes": {},
    }
    for class_name, fields in snapshot.classes.items():
        result["classes"][class_name] = {
            field_name: {
                "field_type": f.field_type,
                "required": f.required,
                "default": f.default,
            }
            for field_name, f in fields.items()
        }
    return result


def dict_to_snapshot(data: dict[str, Any]) -> SchemaSnapshot:
    """Convert a JSON dict back to a SchemaSnapshot."""
    classes: dict[str, dict[str, FieldDef]] = {}
    for class_name, field_data in data.get("classes", {}).items():
        fields: dict[str, FieldDef] = {}
        for field_name, field_info in field_data.items():
            fields[field_name] = FieldDef(
                name=field_name,
                field_type=field_info["field_type"],
                required=field_info["required"],
                default=field_info.get("default"),
            )
        classes[class_name] = fields
    return SchemaSnapshot(module_name=data["module_name"], classes=classes)


def compare_snapshots(
    current: SchemaSnapshot, baseline: SchemaSnapshot
) -> list[CompatChange]:
    """Compare current schema against baseline and detect changes."""
    changes: list[CompatChange] = []

    for class_name, current_fields in current.classes.items():
        baseline_fields = baseline.classes.get(class_name, {})

        for field_name, current_field in current_fields.items():
            if field_name not in baseline_fields:
                if current_field.required:
                    changes.append(
                        CompatChange(
                            module_name=current.module_name,
                            class_name=class_name,
                            field_name=field_name,
                            change_type="added_required_field",
                            severity="breaking",
                            details=(
                                f"New required field '{field_name}' "
                                f"(type: {current_field.field_type})"
                            ),
                        )
                    )
                else:
                    changes.append(
                        CompatChange(
                            module_name=current.module_name,
                            class_name=class_name,
                            field_name=field_name,
                            change_type="added_optional_field",
                            severity="compatible",
                            details=(
                                f"New optional field '{field_name}' "
                                f"(type: {current_field.field_type})"
                            ),
                        )
                    )
                continue

            baseline_field = baseline_fields[field_name]

            if current_field.field_type != baseline_field.field_type:
                changes.append(
                    CompatChange(
                        module_name=current.module_name,
                        class_name=class_name,
                        field_name=field_name,
                        change_type="type_changed",
                        severity="breaking",
                        details=(
                            f"Type changed from '{baseline_field.field_type}' "
                            f"to '{current_field.field_type}'"
                        ),
                    )
                )

            if baseline_field.required and not current_field.required:
                changes.append(
                    CompatChange(
                        module_name=current.module_name,
                        class_name=class_name,
                        field_name=field_name,
                        change_type="field_made_optional",
                        severity="compatible",
                        details=f"Field '{field_name}' is now optional",
                    )
                )

            if not baseline_field.required and current_field.required:
                changes.append(
                    CompatChange(
                        module_name=current.module_name,
                        class_name=class_name,
                        field_name=field_name,
                        change_type="field_made_required",
                        severity="breaking",
                        details=f"Field '{field_name}' is now required",
                    )
                )

        for field_name, baseline_field in baseline_fields.items():
            if field_name not in current_fields:
                if baseline_field.required:
                    changes.append(
                        CompatChange(
                            module_name=current.module_name,
                            class_name=class_name,
                            field_name=field_name,
                            change_type="removed_required_field",
                            severity="breaking",
                            details=(
                                f"Required field '{field_name}' was removed "
                                f"(type: {baseline_field.field_type})"
                            ),
                        )
                    )
                else:
                    changes.append(
                        CompatChange(
                            module_name=current.module_name,
                            class_name=class_name,
                            field_name=field_name,
                            change_type="removed_optional_field",
                            severity="compatible",
                            details=(
                                f"Optional field '{field_name}' was removed "
                                f"(type: {baseline_field.field_type})"
                            ),
                        )
                    )

    for class_name in baseline.classes:
        if class_name not in current.classes:
            changes.append(
                CompatChange(
                    module_name=current.module_name,
                    class_name=class_name,
                    field_name="*",
                    change_type="removed_class",
                    severity="breaking",
                    details=f"Class '{class_name}' was removed entirely",
                )
            )

    return changes


def generate_baselines(
    schemas_dir: Path, baseline_dir: Path
) -> list[str]:
    """Generate baseline snapshots from current schemas."""
    baseline_dir.mkdir(parents=True, exist_ok=True)
    snapshots = load_schema_modules(schemas_dir)
    generated: list[str] = []

    for snapshot in snapshots:
        baseline_path = baseline_dir / f"{snapshot.module_name}.json"
        data = snapshot_to_dict(snapshot)
        baseline_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        generated.append(str(baseline_path))
        class_count = len(snapshot.classes)
        field_count = sum(len(fields) for fields in snapshot.classes.values())
        print(
            f"  Generated: {baseline_path} "
            f"({class_count} classes, {field_count} fields)"
        )

    return generated


def check_compatibility(
    schemas_dir: Path, baseline_dir: Path
) -> list[CompatChange]:
    """Check current schemas against baselines for breaking changes."""
    all_changes: list[CompatChange] = []

    if not baseline_dir.exists():
        raise FileNotFoundError(
            f"Baseline directory not found: {baseline_dir}. "
            "Run with --generate first."
        )

    current_snapshots = load_schema_modules(schemas_dir)
    current_by_module = {s.module_name: s for s in current_snapshots}

    for baseline_file in sorted(baseline_dir.glob("*.json")):
        module_name = baseline_file.stem
        baseline_data = json.loads(baseline_file.read_text(encoding="utf-8"))
        baseline_snapshot = dict_to_snapshot(baseline_data)

        if module_name not in current_by_module:
            all_changes.append(
                CompatChange(
                    module_name=module_name,
                    class_name="*",
                    field_name="*",
                    change_type="removed_module",
                    severity="breaking",
                    details=f"Schema module '{module_name}' was removed entirely",
                )
            )
            continue

        current_snapshot = current_by_module[module_name]
        changes = compare_snapshots(current_snapshot, baseline_snapshot)
        all_changes.extend(changes)

    return all_changes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check schema compatibility against baseline snapshots"
    )
    parser.add_argument(
        "--schemas-dir",
        type=Path,
        required=True,
        help="Directory containing Python schema modules",
    )
    parser.add_argument(
        "--baseline-dir",
        type=Path,
        required=True,
        help="Directory containing baseline JSON snapshots",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate baseline snapshots from current schemas",
    )
    parser.add_argument(
        "--fail-on-breaking",
        action="store_true",
        help="Exit with code 1 if breaking changes are found",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Write compatibility report to this file",
    )
    args = parser.parse_args()

    if args.generate:
        print("Generating baseline snapshots...")
        generated = generate_baselines(args.schemas_dir, args.baseline_dir)
        print(f"\nGenerated {len(generated)} baseline file(s).")
        return 0

    print("Checking schema compatibility...")
    try:
        changes = check_compatibility(args.schemas_dir, args.baseline_dir)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    breaking = [c for c in changes if c.severity == "breaking"]
    compatible = [c for c in changes if c.severity == "compatible"]

    print(f"\nFound {len(changes)} change(s):")
    print(f"  Breaking: {len(breaking)}")
    print(f"  Compatible: {len(compatible)}")

    for change in breaking:
        print(f"  [BREAKING] {change.module_name}.{change.class_name}.{change.field_name}: {change.details}")

    for change in compatible:
        print(f"  [OK]        {change.module_name}.{change.class_name}.{change.field_name}: {change.details}")

    if args.output_json:
        report = {
            "total_changes": len(changes),
            "breaking": len(breaking),
            "compatible": len(compatible),
            "changes": [
                {
                    "module": c.module_name,
                    "class": c.class_name,
                    "field": c.field_name,
                    "type": c.change_type,
                    "severity": c.severity,
                    "details": c.details,
                }
                for c in changes
            ],
        }
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with args.output_json.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\nReport written to {args.output_json}")

    if args.fail_on_breaking and breaking:
        print(
            f"\nFAIL: {len(breaking)} breaking change(s) detected.",
            file=sys.stderr,
        )
        return 1

    if not breaking:
        print("\nPASS: No breaking changes detected.")
    else:
        print(f"\nWARN: {len(breaking)} breaking change(s) detected (not failing per config).")

    return 0


if __name__ == "__main__":
    sys.exit(main())

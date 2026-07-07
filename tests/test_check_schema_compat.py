"""Tests for check_schema_compat.py script."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from check_schema_compat import (
    CompatChange,
    FieldDef,
    SchemaSnapshot,
    check_compatibility,
    compare_snapshots,
    extract_classes_from_module,
    generate_baselines,
    snapshot_to_dict,
)


SAMPLE_SCHEMA = '''
class MaterialBase(BaseModel):
    name: str
    density_kg_m3: float | None = None
    melting_point_k: float | None = None

class DataSource(BaseModel):
    title: str
    doi: str | None = None
    url: str | None = None
'''


@pytest.fixture()
def sample_snapshot() -> SchemaSnapshot:
    return SchemaSnapshot(
        module_name="test",
        classes={
            "MaterialBase": {
                "name": FieldDef(name="name", field_type="str", required=True, default=None),
                "density_kg_m3": FieldDef(name="density_kg_m3", field_type="float | None", required=False, default=None),
            },
            "DataSource": {
                "title": FieldDef(name="title", field_type="str", required=True, default=None),
                "doi": FieldDef(name="doi", field_type="str | None", required=False, default=None),
            },
        },
    )


@pytest.fixture()
def sample_baseline_dir(tmp_path: Path, sample_snapshot: SchemaSnapshot) -> Path:
    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir()
    data = snapshot_to_dict(sample_snapshot)
    (baseline_dir / "test.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )
    return baseline_dir


@pytest.fixture()
def sample_schemas_dir(tmp_path: Path) -> Path:
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    (schemas_dir / "materials.py").write_text(SAMPLE_SCHEMA, encoding="utf-8")
    return schemas_dir


class TestExtractClasses:
    @pytest.mark.unit
    def test_extracts_pydantic_classes(self) -> None:
        classes = extract_classes_from_module(SAMPLE_SCHEMA)
        assert "MaterialBase" in classes
        assert "DataSource" in classes
        assert "name" in classes["MaterialBase"]

    @pytest.mark.unit
    def test_empty_module(self) -> None:
        classes = extract_classes_from_module("# empty file\n")
        assert classes == {}

    @pytest.mark.unit
    def test_invalid_syntax(self) -> None:
        classes = extract_classes_from_module("class {")
        assert classes == {}

    @pytest.mark.unit
    def test_ignores_classes_without_fields(self) -> None:
        source = "class NoFields(BaseModel):\n    pass\n"
        classes = extract_classes_from_module(source)
        assert classes == {}


class TestCompareSnapshots:
    @pytest.mark.unit
    def test_no_changes(self, sample_snapshot: SchemaSnapshot) -> None:
        changes = compare_snapshots(sample_snapshot, sample_snapshot)
        assert changes == []

    @pytest.mark.unit
    def test_detects_removed_required_field(self, sample_snapshot: SchemaSnapshot) -> None:
        current = SchemaSnapshot(
            module_name="test",
            classes={
                "MaterialBase": {
                    "density_kg_m3": FieldDef(
                        name="density_kg_m3",
                        field_type="float | None",
                        required=False,
                        default=None,
                    ),
                },
                "DataSource": {
                    "title": FieldDef(name="title", field_type="str", required=True, default=None),
                    "doi": FieldDef(name="doi", field_type="str | None", required=False, default=None),
                },
            },
        )
        changes = compare_snapshots(current, sample_snapshot)
        breaking = [c for c in changes if c.severity == "breaking"]
        removed_fields = [c for c in breaking if c.change_type == "removed_required_field"]
        assert any(c.field_name == "name" for c in removed_fields)

    @pytest.mark.unit
    def test_detects_added_required_field(self, sample_snapshot: SchemaSnapshot) -> None:
        current = SchemaSnapshot(
            module_name="test",
            classes={
                "MaterialBase": {
                    "name": FieldDef(name="name", field_type="str", required=True, default=None),
                    "density_kg_m3": FieldDef(name="density_kg_m3", field_type="float | None", required=False, default=None),
                    "new_field": FieldDef(name="new_field", field_type="str", required=True, default=None),
                },
                "DataSource": {
                    "title": FieldDef(name="title", field_type="str", required=True, default=None),
                    "doi": FieldDef(name="doi", field_type="str | None", required=False, default=None),
                },
            },
        )
        changes = compare_snapshots(current, sample_snapshot)
        breaking = [c for c in changes if c.severity == "breaking"]
        assert any(c.field_name == "new_field" for c in breaking)

    @pytest.mark.unit
    def test_detects_type_change(self, sample_snapshot: SchemaSnapshot) -> None:
        current = SchemaSnapshot(
            module_name="test",
            classes={
                "MaterialBase": {
                    "name": FieldDef(name="name", field_type="int", required=True, default=None),
                    "density_kg_m3": FieldDef(name="density_kg_m3", field_type="float | None", required=False, default=None),
                },
                "DataSource": {
                    "title": FieldDef(name="title", field_type="str", required=True, default=None),
                    "doi": FieldDef(name="doi", field_type="str | None", required=False, default=None),
                },
            },
        )
        changes = compare_snapshots(current, sample_snapshot)
        type_changes = [c for c in changes if c.change_type == "type_changed"]
        assert len(type_changes) == 1
        assert type_changes[0].field_name == "name"

    @pytest.mark.unit
    def test_detects_removed_class(self, sample_snapshot: SchemaSnapshot) -> None:
        current = SchemaSnapshot(
            module_name="test",
            classes={
                "MaterialBase": {
                    "name": FieldDef(name="name", field_type="str", required=True, default=None),
                    "density_kg_m3": FieldDef(name="density_kg_m3", field_type="float | None", required=False, default=None),
                },
            },
        )
        changes = compare_snapshots(current, sample_snapshot)
        removed = [c for c in changes if c.change_type == "removed_class"]
        assert len(removed) == 1
        assert removed[0].class_name == "DataSource"

    @pytest.mark.unit
    def test_field_made_optional_is_compatible(self, sample_snapshot: SchemaSnapshot) -> None:
        current = SchemaSnapshot(
            module_name="test",
            classes={
                "MaterialBase": {
                    "name": FieldDef(name="name", field_type="str | None", required=False, default=None),
                    "density_kg_m3": FieldDef(name="density_kg_m3", field_type="float | None", required=False, default=None),
                },
                "DataSource": {
                    "title": FieldDef(name="title", field_type="str", required=True, default=None),
                    "doi": FieldDef(name="doi", field_type="str | None", required=False, default=None),
                },
            },
        )
        changes = compare_snapshots(current, sample_snapshot)
        compat = [c for c in changes if c.severity == "compatible"]
        assert any(c.change_type == "field_made_optional" for c in compat)


class TestSnapshotToDict:
    @pytest.mark.unit
    def test_round_trip(self, sample_snapshot: SchemaSnapshot) -> None:
        data = snapshot_to_dict(sample_snapshot)
        assert data["module_name"] == "test"
        assert "MaterialBase" in data["classes"]
        assert data["classes"]["MaterialBase"]["name"]["field_type"] == "str"


class TestCheckCompatibility:
    @pytest.mark.unit
    def test_no_changes_detected(
        self, sample_schemas_dir: Path, tmp_path: Path
    ) -> None:
        baseline_dir = tmp_path / "baseline"
        generate_baselines(sample_schemas_dir, baseline_dir)
        changes = check_compatibility(sample_schemas_dir, baseline_dir)
        assert changes == []

    @pytest.mark.unit
    def test_missing_baseline_raises(self, tmp_path: Path) -> None:
        schemas_dir = tmp_path / "schemas"
        schemas_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="Baseline directory not found"):
            check_compatibility(schemas_dir, tmp_path / "missing_baseline")


class TestGenerateBaselines:
    @pytest.mark.unit
    def test_creates_baseline_files(
        self, sample_schemas_dir: Path, tmp_path: Path
    ) -> None:
        baseline_dir = tmp_path / "baselines"
        generated = generate_baselines(sample_schemas_dir, baseline_dir)
        assert len(generated) == 1
        assert (baseline_dir / "materials.json").exists()

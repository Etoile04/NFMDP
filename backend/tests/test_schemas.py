"""Tests for Pydantic schemas: extraction_submit, extraction_figure, materials,
ontology."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

import pytest

from nfm_backend.schemas.extraction_figure import (
    ExtractionFigureCreate,
    ExtractionFigureRead,
)
from nfm_backend.schemas.extraction_submit import (
    ConflictStrategy,
    ExtractionSubmitRequest,
    ExtractionSubmitResponse,
    FigureType,
    MultimodalOptions,
)
from nfm_backend.schemas.materials import (
    DataSource,
    Material,
    PaginatedResponse,
    PropertyMeasurement,
)
from nfm_backend.schemas.ontology import (  # noqa: F401
    KGEdge,
    KGNode,
    RelationshipType,
    SyncResult,
    SyncStatus,
)

# ---------------------------------------------------------------------------
# extraction_submit.py schemas
# ---------------------------------------------------------------------------


class TestFigureType:
    def test_all_values(self) -> None:
        assert FigureType.CHART == "chart"
        assert FigureType.DIAGRAM == "diagram"
        assert FigureType.PHOTOGRAPH == "photograph"
        assert FigureType.PLOT == "plot"
        assert FigureType.TABLE_FIGURE == "table_figure"
        assert FigureType.SCHEMATIC == "schematic"
        assert FigureType.MICROGRAPH == "micrograph"
        assert FigureType.OTHER == "other"


class TestConflictStrategy:
    def test_all_values(self) -> None:
        assert ConflictStrategy.VLM_PREFERRED == "vlm_preferred"
        assert ConflictStrategy.OCR_PREFERRED == "ocr_preferred"
        assert ConflictStrategy.MERGE == "merge"
        assert ConflictStrategy.HIGHEST_CONFIDENCE == "highest_confidence"


class TestMultimodalOptions:
    def test_defaults(self) -> None:
        opts = MultimodalOptions()
        assert opts.extract_figures is True
        assert opts.extract_tables is True
        assert opts.figure_types is None
        assert opts.confidence_threshold == 0.5
        assert opts.conflict_strategy == ConflictStrategy.HIGHEST_CONFIDENCE

    def test_custom_values(self) -> None:
        opts = MultimodalOptions(
            extract_figures=False,
            confidence_threshold=0.9,
            conflict_strategy=ConflictStrategy.VLM_PREFERRED,
            figure_types=[FigureType.PLOT, FigureType.CHART],
        )
        assert opts.extract_figures is False
        assert opts.confidence_threshold == 0.9
        assert len(opts.figure_types) == 2

    def test_confidence_bounds(self) -> None:
        with pytest.raises(Exception, match="confidence_threshold"):
            MultimodalOptions(confidence_threshold=1.5)
        with pytest.raises(Exception, match="confidence_threshold"):
            MultimodalOptions(confidence_threshold=-0.1)


class TestExtractionSubmitRequest:
    def test_defaults(self) -> None:
        req = ExtractionSubmitRequest()
        assert req.source_url is None
        assert req.source_filename is None
        assert req.material_id is None
        assert req.language == "en"
        assert req.pages is None
        assert isinstance(req.options, MultimodalOptions)

    def test_full_request(self) -> None:
        req = ExtractionSubmitRequest(
            source_url="https://example.com/paper.pdf",
            source_filename="paper.pdf",
            material_id=str(uuid4()),
            language="zh",
            pages=[1, 2, 3],
        )
        assert req.source_url == "https://example.com/paper.pdf"
        assert req.pages == [1, 2, 3]
        assert req.language == "zh"


class TestExtractionSubmitResponse:
    def test_queued_status(self) -> None:
        resp = ExtractionSubmitResponse(job_id="abc-123", status="queued")
        assert resp.job_id == "abc-123"
        assert resp.status == "queued"
        assert resp.estimated_duration_seconds is None

    def test_processing_status(self) -> None:
        resp = ExtractionSubmitResponse(
            job_id="abc-123",
            status="processing",
            estimated_duration_seconds=120,
        )
        assert resp.estimated_duration_seconds == 120


# ---------------------------------------------------------------------------
# extraction_figure.py schemas
# ---------------------------------------------------------------------------


class TestExtractionFigureCreate:
    def test_minimal(self) -> None:
        fig = ExtractionFigureCreate(
            job_id=uuid4(),
            page_number=1,
            figure_type="plot",
            extracted_data={"key": "value"},
        )
        assert fig.bounding_box is None
        assert fig.caption is None
        assert fig.image_path is None
        assert fig.confidence == 0.0
        assert fig.extraction_method is None
        assert fig.source_id is None

    def test_full(self) -> None:
        fig = ExtractionFigureCreate(
            job_id=uuid4(),
            page_number=5,
            figure_type="chart",
            extracted_data={"yield": 350},
            source_id=uuid4(),
            bounding_box={"x": 0, "y": 0},
            caption="Stress-strain curve",
            image_path="/figures/fig1.png",
            confidence=0.95,
            extraction_method="vlm",
        )
        assert fig.confidence == 0.95
        assert fig.caption == "Stress-strain curve"

    def test_page_number_minimum(self) -> None:
        with pytest.raises(Exception, match="page_number"):
            ExtractionFigureCreate(
                job_id=uuid4(),
                page_number=0,
                figure_type="plot",
                extracted_data={},
            )


class TestExtractionFigureRead:
    def test_from_attributes(self) -> None:
        fig = ExtractionFigureRead(
            id=uuid4(),
            job_id=uuid4(),
            page_number=1,
            figure_type="plot",
            extracted_data={},
            created_at=datetime(2026, 1, 1),
        )
        assert fig.figure_type == "plot"

    def test_confidence_bounds(self) -> None:
        with pytest.raises(Exception, match="confidence"):
            ExtractionFigureRead(
                id=uuid4(),
                job_id=uuid4(),
                page_number=1,
                figure_type="plot",
                extracted_data={},
                confidence=1.5,
                created_at=datetime(2026, 1, 1),
            )


# ---------------------------------------------------------------------------
# materials.py schemas
# ---------------------------------------------------------------------------


class TestDataSource:
    def test_minimal(self) -> None:
        ds = DataSource(id=uuid4(), title="Paper Title")
        assert ds.title == "Paper Title"
        assert ds.doi is None
        assert ds.journal is None

    def test_full(self) -> None:
        ds = DataSource(
            id=uuid4(),
            title="Full Paper",
            doi="10.1234/test",
            journal="Nature",
            year=2025,
            source_type="journal_article",
            url="https://doi.org/10.1234/test",
            created_at=datetime(2026, 1, 1),
        )
        assert ds.doi == "10.1234/test"
        assert ds.year == 2025


class TestMaterial:
    def test_minimal(self) -> None:
        m = Material(id=uuid4(), name="UO2")
        assert m.name == "UO2"
        assert m.chemical_formula is None
        assert m.category_id is None

    def test_full(self) -> None:
        m = Material(
            id=uuid4(),
            name="Uranium Dioxide",
            name_zh="二氧化铀",
            chemical_formula="UO2",
            material_type="ceramic",
            crystal_structure="fluorite",
            density_kg_m3=10970.0,
            melting_point_k=3138.0,
            description="Nuclear fuel material",
            category_id=uuid4(),
            created_at=datetime(2026, 1, 1),
        )
        assert m.density_kg_m3 == 10970.0
        assert m.melting_point_k == 3138.0


class TestPropertyMeasurement:
    def test_minimal(self) -> None:
        pm = PropertyMeasurement(
            id=uuid4(),
            property_type_id=uuid4(),
            material_id=uuid4(),
        )
        assert pm.value_scalar is None
        assert pm.unit is None

    def test_full(self) -> None:
        pm = PropertyMeasurement(
            id=uuid4(),
            property_type_id=uuid4(),
            material_id=uuid4(),
            dataset_id=uuid4(),
            data_source_id=uuid4(),
            value_type="scalar",
            value_scalar=10970.0,
            unit="kg/m³",
            uncertainty_value=10.0,
            uncertainty_type="absolute",
            conditions={"temperature": "298K"},
            confidence="high",
            method="experimental",
            notes="Room temperature measurement",
            review_status="approved",
            created_at=datetime(2026, 1, 1),
        )
        assert pm.value_scalar == 10970.0
        assert pm.confidence == "high"


class TestPaginatedResponse:
    def test_empty(self) -> None:
        resp = PaginatedResponse(items=[], total=0, page=1, limit=20)
        assert resp.items == []
        assert resp.total == 0

    def test_with_items(self) -> None:
        items: list[Any] = [{"id": uuid4(), "name": "UO2"}]
        resp = PaginatedResponse(items=items, total=1, page=1, limit=20)
        assert len(resp.items) == 1


# ---------------------------------------------------------------------------
# ontology.py schemas
# ---------------------------------------------------------------------------


class TestRelationshipType:
    def test_all_values(self) -> None:
        assert RelationshipType.HAS_PROPERTY == "HAS_PROPERTY"
        assert RelationshipType.MEASURED_BY == "MEASURED_BY"
        assert RelationshipType.HAS_CATEGORY == "HAS_CATEGORY"
        assert RelationshipType.RELATED_TO == "RELATED_TO"
        assert RelationshipType.CONTAINS == "CONTAINS"
        assert RelationshipType.INSTANCE_OF == "INSTANCE_OF"
        assert RelationshipType.SUBCLASS_OF == "SUBCLASS_OF"
        assert RelationshipType.HAS_UNIT == "HAS_UNIT"
        assert RelationshipType.HAS_SOURCE == "HAS_SOURCE"
        assert RelationshipType.DERIVED_FROM == "DERIVED_FROM"


class TestKGNode:
    def test_minimal(self) -> None:
        node = KGNode(
            id=uuid4(),
            corpus_id=uuid4(),
            ontology_id="MAT:UO2",
            node_type="material",
            name="UO2",
        )
        assert node.name == "UO2"
        assert node.synonyms == []
        assert node.properties == {}
        assert node.synced_to_graph is False

    def test_full(self) -> None:
        node = KGNode(
            id=uuid4(),
            corpus_id=uuid4(),
            ontology_id="MAT:UO2",
            node_type="material",
            name="Uranium Dioxide",
            name_zh="二氧化铀",
            uri="http://example.org/UO2",
            definition="A ceramic nuclear fuel material",
            synonyms=["UO2", "uranium oxide"],
            properties={"density": 10970},
            synced_to_graph=True,
        )
        assert len(node.synonyms) == 2
        assert node.synced_to_graph is True

    def test_frozen(self) -> None:
        node = KGNode(
            id=uuid4(),
            corpus_id=uuid4(),
            ontology_id="MAT:UO2",
            node_type="material",
            name="UO2",
        )
        with pytest.raises(AttributeError):
            node.name = "changed"


class TestKGEdge:
    def test_minimal(self) -> None:
        edge = KGEdge(
            id=uuid4(),
            corpus_id=uuid4(),
            source_node_id=uuid4(),
            target_node_id=uuid4(),
            relationship_type=RelationshipType.HAS_PROPERTY,
        )
        assert edge.label is None
        assert edge.weight is None
        assert edge.properties == {}

    def test_full(self) -> None:
        edge = KGEdge(
            id=uuid4(),
            corpus_id=uuid4(),
            source_node_id=uuid4(),
            target_node_id=uuid4(),
            relationship_type=RelationshipType.MEASURED_BY,
            label="measured_by",
            properties={"method": "XRD"},
            weight=0.95,
            synced_to_graph=True,
        )
        assert edge.weight == 0.95

    def test_frozen(self) -> None:
        edge = KGEdge(
            id=uuid4(),
            corpus_id=uuid4(),
            source_node_id=uuid4(),
            target_node_id=uuid4(),
            relationship_type=RelationshipType.HAS_PROPERTY,
        )
        with pytest.raises(AttributeError):
            edge.weight = 1.0


class TestSyncResult:
    def test_success(self) -> None:
        result = SyncResult(
            corpus_id="corp-1",
            mode="full",
            nodes_synced=10,
            edges_synced=5,
        )
        assert result.success is True
        assert result.total_synced == 15

    def test_with_errors(self) -> None:
        result = SyncResult(
            corpus_id="corp-1",
            mode="incremental",
            nodes_failed=1,
            errors=("Node sync failed",),
        )
        assert result.success is False

    def test_empty_corpus(self) -> None:
        result = SyncResult(corpus_id="corp-1", mode="full")
        assert result.nodes_synced == 0
        assert result.success is True

    def test_frozen(self) -> None:
        result = SyncResult(corpus_id="corp-1", mode="full")
        with pytest.raises(AttributeError):
            result.nodes_synced = 5


class TestSyncStatus:
    def test_fully_synced(self) -> None:
        status = SyncStatus(
            corpus_id="corp-1",
            total_nodes=10,
            synced_nodes=10,
            unsynced_nodes=0,
            total_edges=5,
            synced_edges=5,
            unsynced_edges=0,
            graph_exists=True,
        )
        assert status.is_fully_synced is True

    def test_partially_synced(self) -> None:
        status = SyncStatus(
            corpus_id="corp-1",
            total_nodes=10,
            synced_nodes=8,
            unsynced_nodes=2,
            total_edges=5,
            synced_edges=5,
            unsynced_edges=0,
            graph_exists=True,
        )
        assert status.is_fully_synced is False

    def test_defaults(self) -> None:
        status = SyncStatus(corpus_id="corp-1")
        assert status.total_nodes == 0
        assert status.graph_exists is False
        assert status.is_fully_synced is True

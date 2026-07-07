"""Tests for ontology_sync — dual-write service between relational tables and AGE graph.

Mocks SQLAlchemy connections to test sync logic without a real database.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError

from nfm_backend.schemas.ontology import (
    KGEdge,
    KGNode,
    RelationshipType,
    SyncResult,
    SyncStatus,
)
from nfm_backend.services.ontology_sync import (
    _ensure_age_session,
    _graph_name,
    _row_to_kg_edge,
    _row_to_kg_node,
    get_sync_status,
    rebuild_ontology_graph,
    sync_corpus_to_graph,
)

SAMPLE_CORPUS_ID = str(uuid4())
SAMPLE_NODE_ID = uuid4()
SAMPLE_EDGE_ID = uuid4()
SAMPLE_SOURCE_ID = uuid4()
SAMPLE_TARGET_ID = uuid4()


def _make_node_row(**overrides: Any) -> Any:
    defaults: dict[str, Any] = {
        "id": SAMPLE_NODE_ID,
        "corpus_id": uuid4(),
        "ontology_id": "MAT:UO2",
        "node_type": "material",
        "name": "UO2",
        "name_zh": "二氧化铀",
        "uri": "http://example.org/UO2",
        "definition": "A ceramic nuclear fuel",
        "synonyms": ["UO2", "uranium dioxide"],
        "properties": {"density": 10970},
        "synced_to_graph": False,
    }
    defaults.update(overrides)
    row = MagicMock()
    for key, value in defaults.items():
        setattr(row, key, value)
    return row


def _make_edge_row(**overrides: Any) -> Any:
    defaults: dict[str, Any] = {
        "id": SAMPLE_EDGE_ID,
        "corpus_id": uuid4(),
        "source_node_id": SAMPLE_SOURCE_ID,
        "target_node_id": SAMPLE_TARGET_ID,
        "relationship_type": "HAS_PROPERTY",
        "label": "has_property",
        "properties": {"method": "XRD"},
        "weight": 0.95,
        "synced_to_graph": False,
    }
    defaults.update(overrides)
    row = MagicMock()
    for key, value in defaults.items():
        setattr(row, key, value)
    return row


# ---------------------------------------------------------------------------
# _row_to_kg_node
# ---------------------------------------------------------------------------


class TestRowToKGNode:
    def test_full_row(self) -> None:
        row = _make_node_row()
        node = _row_to_kg_node(row)
        assert node.id == SAMPLE_NODE_ID
        assert node.ontology_id == "MAT:UO2"
        assert node.name == "UO2"
        assert node.name_zh == "二氧化铀"
        assert node.synonyms == ["UO2", "uranium dioxide"]
        assert node.properties == {"density": 10970}

    def test_null_optional_fields(self) -> None:
        row = _make_node_row(
            name_zh=None, uri=None, definition=None, synonyms=None, properties=None
        )
        node = _row_to_kg_node(row)
        assert node.name_zh is None
        assert node.synonyms == []
        assert node.properties == {}

    def test_synced_flag(self) -> None:
        row = _make_node_row(synced_to_graph=True)
        node = _row_to_kg_node(row)
        assert node.synced_to_graph is True


# ---------------------------------------------------------------------------
# _row_to_kg_edge
# ---------------------------------------------------------------------------


class TestRowToKGEdge:
    def test_full_row(self) -> None:
        row = _make_edge_row()
        edge = _row_to_kg_edge(row)
        assert edge.id == SAMPLE_EDGE_ID
        assert edge.relationship_type == RelationshipType.HAS_PROPERTY
        assert edge.label == "has_property"
        assert edge.weight == 0.95

    def test_null_optional_fields(self) -> None:
        row = _make_edge_row(label=None, properties=None, weight=None)
        edge = _row_to_kg_edge(row)
        assert edge.label is None
        assert edge.properties == {}
        assert edge.weight is None


# ---------------------------------------------------------------------------
# _graph_name
# ---------------------------------------------------------------------------


class TestGraphName:
    def test_formats_correctly(self) -> None:
        assert _graph_name("abc123") == "ontology_abc123"

    def test_with_uuid(self) -> None:
        cid = str(uuid4())
        assert _graph_name(cid).startswith("ontology_")


# ---------------------------------------------------------------------------
# _ensure_age_session
# ---------------------------------------------------------------------------


class TestEnsureAgeSession:
    def test_propagates_operational_error(self) -> None:
        conn = MagicMock()
        conn.execute.side_effect = OperationalError("dummy", "dummy", "dummy")

        with pytest.raises(RuntimeError, match="AGE session"):
            _ensure_age_session(conn)

    def test_success_passes(self) -> None:
        conn = MagicMock()
        conn.execute.return_value = None
        _ensure_age_session(conn)  # Should not raise


# ---------------------------------------------------------------------------
# sync_corpus_to_graph
# ---------------------------------------------------------------------------


def _make_safe_conn(
    node_rows: list[Any] | None = None,
    edge_rows: list[Any] | None = None,
    graph_exists: bool = True,
) -> MagicMock:
    """Create a mock conn that avoids the Cypher $-format issue."""
    conn = MagicMock()

    def fake_execute(*args, **kwargs):
        sql_text = str(args[0]) if args else ""
        if "SELECT" in sql_text and "kg_nodes" in sql_text:
            result = MagicMock()
            result.fetchall.return_value = node_rows or []
            return result
        if "SELECT" in sql_text and "kg_edges" in sql_text:
            result = MagicMock()
            result.fetchall.return_value = edge_rows or []
            return result
        if "EXISTS" in sql_text:
            result = MagicMock()
            result.scalar.return_value = graph_exists
            return result
        return None

    conn.execute.side_effect = fake_execute
    return conn


class TestSyncCorpusFull:
    def test_empty_corpus_returns_success(self) -> None:
        conn = _make_safe_conn(node_rows=[], edge_rows=[])
        result = sync_corpus_to_graph(conn, SAMPLE_CORPUS_ID, mode="full")
        assert result.corpus_id == SAMPLE_CORPUS_ID
        assert result.mode == "full"
        assert result.success is True
        assert result.nodes_synced == 0
        assert result.edges_synced == 0

    def test_invalid_mode_catches_as_error(self) -> None:
        conn = MagicMock()
        conn.execute.return_value = None
        result = sync_corpus_to_graph(conn, SAMPLE_CORPUS_ID, mode="bad_mode")
        assert result.success is False
        assert any("Invalid sync mode" in e for e in result.errors)


class TestSyncCorpusIncremental:
    def test_graph_not_exists_catches_error(self) -> None:
        conn = _make_safe_conn(graph_exists=False)
        result = sync_corpus_to_graph(
            conn, SAMPLE_CORPUS_ID, mode="incremental"
        )
        assert result.success is False
        assert any("does not exist" in e for e in result.errors)

    def test_incremental_sync_empty(self) -> None:
        conn = _make_safe_conn(
            node_rows=[], edge_rows=[], graph_exists=True
        )
        result = sync_corpus_to_graph(
            conn, SAMPLE_CORPUS_ID, mode="incremental"
        )
        assert result.success is True


# ---------------------------------------------------------------------------
# rebuild_ontology_graph
# ---------------------------------------------------------------------------


class TestRebuildOntologyGraph:
    def test_delegates_to_full_sync(self) -> None:
        conn = MagicMock()

        with patch(
            "nfm_backend.services.ontology_sync.sync_corpus_to_graph"
        ) as mock_sync:
            mock_sync.return_value = SyncResult(
                corpus_id=SAMPLE_CORPUS_ID, mode="full"
            )
            result = rebuild_ontology_graph(conn, SAMPLE_CORPUS_ID)

        assert result.mode == "full"
        mock_sync.assert_called_once_with(
            conn, SAMPLE_CORPUS_ID, mode="full"
        )


# ---------------------------------------------------------------------------
# get_sync_status
# ---------------------------------------------------------------------------


class TestGetSyncStatus:
    def test_returns_sync_status(self) -> None:
        node_row = MagicMock()
        node_row.total = 10
        node_row.synced = 8
        node_row.unsynced = 2

        edge_row = MagicMock()
        edge_row.total = 5
        edge_row.synced = 3
        edge_row.unsynced = 2

        def fake_execute(*args, **kwargs):
            sql = str(args[0]) if args else ""
            if "EXISTS" in sql:
                result = MagicMock()
                result.scalar.return_value = True
                return result
            if "kg_nodes" in sql:
                result = MagicMock()
                result.fetchone.return_value = node_row
                return result
            if "kg_edges" in sql:
                result = MagicMock()
                result.fetchone.return_value = edge_row
                return result
            return None

        conn = MagicMock()
        conn.execute.side_effect = fake_execute

        status = get_sync_status(conn, SAMPLE_CORPUS_ID)
        assert status.total_nodes == 10
        assert status.synced_nodes == 8
        assert status.unsynced_nodes == 2
        assert status.total_edges == 5
        assert status.graph_exists is True
        assert status.is_fully_synced is False

    def test_empty_corpus_status(self) -> None:
        def fake_execute(*args, **kwargs):
            sql = str(args[0]) if args else ""
            if "EXISTS" in sql:
                result = MagicMock()
                result.scalar.return_value = False
                return result
            result = MagicMock()
            result.fetchone.return_value = None
            return result

        conn = MagicMock()
        conn.execute.side_effect = fake_execute

        status = get_sync_status(conn, SAMPLE_CORPUS_ID)
        assert status.total_nodes == 0
        assert status.graph_exists is False
        assert status.is_fully_synced is True

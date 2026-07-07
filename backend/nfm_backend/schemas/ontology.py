"""Ontology data models for NVL contract and AGE graph sync.

Defines the relational source-of-truth models (KGNode, KGEdge) that map
to kg_nodes / kg_edges tables, and sync result types used by the
dual-write service (ontology_sync.py).

Reference: CTO Spec §2.2-2.4, ADR-NFM-820-1, ADR-NFM-820-2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

# ---------------------------------------------------------------------------
# Relationship type enum — maps to AGE edge labels
# ---------------------------------------------------------------------------

class RelationshipType(StrEnum):
    """Typed edge labels for AGE graph relationships."""

    HAS_PROPERTY = "HAS_PROPERTY"
    MEASURED_BY = "MEASURED_BY"
    HAS_CATEGORY = "HAS_CATEGORY"
    RELATED_TO = "RELATED_TO"
    CONTAINS = "CONTAINS"
    INSTANCE_OF = "INSTANCE_OF"
    SUBCLASS_OF = "SUBCLASS_OF"
    HAS_UNIT = "HAS_UNIT"
    HAS_SOURCE = "HAS_SOURCE"
    DERIVED_FROM = "DERIVED_FROM"


# ---------------------------------------------------------------------------
# Relational source-of-truth models (kg_nodes / kg_edges)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KGNode:
    """Immutable representation of a kg_nodes row (source of truth).

    Maps to the ``kg_nodes`` table created by migration 014 (NFM-832.1).
    """

    id: UUID
    corpus_id: UUID
    ontology_id: str
    node_type: str
    name: str
    name_zh: str | None = None
    uri: str | None = None
    definition: str | None = None
    synonyms: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    synced_to_graph: bool = False
    graph_synced_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class KGEdge:
    """Immutable representation of a kg_edges row (source of truth).

    Maps to the ``kg_edges`` table created by migration 014 (NFM-832.1).
    """

    id: UUID
    corpus_id: UUID
    source_node_id: UUID
    target_node_id: UUID
    relationship_type: RelationshipType
    label: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    weight: float | None = None
    synced_to_graph: bool = False
    graph_synced_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Sync result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SyncResult:
    """Immutable result of a corpus-to-graph sync operation."""

    corpus_id: str
    mode: str
    nodes_synced: int = 0
    edges_synced: int = 0
    nodes_failed: int = 0
    edges_failed: int = 0
    errors: tuple[str, ...] = ()
    duration_seconds: float = 0.0

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def total_synced(self) -> int:
        return self.nodes_synced + self.edges_synced


@dataclass(frozen=True)
class SyncStatus:
    """Immutable snapshot of sync state for a corpus."""

    corpus_id: str
    total_nodes: int = 0
    synced_nodes: int = 0
    unsynced_nodes: int = 0
    total_edges: int = 0
    synced_edges: int = 0
    unsynced_edges: int = 0
    graph_exists: bool = False
    last_synced_at: datetime | None = None

    @property
    def is_fully_synced(self) -> bool:
        return self.unsynced_nodes == 0 and self.unsynced_edges == 0

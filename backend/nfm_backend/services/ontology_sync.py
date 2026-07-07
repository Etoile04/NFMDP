"""Dual-write service: synchronizes ontology data between relational tables
and Apache AGE graph.

Relational tables (kg_nodes, kg_edges) are the source of truth.
The AGE graph is a rebuildable materialized view used for graph queries.

Graph naming convention: ``ontology_{corpus_id}`` (ADR-NFM-820-2).
All Cypher queries execute via PG ``cypher()`` function.

Reference: CTO Spec §2.2-2.4, ADR-NFM-820-1, ADR-NFM-820-2.
"""

from __future__ import annotations

import logging
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError, OperationalError

from nfm_backend.schemas.ontology import (
    KGEdge,
    KGNode,
    RelationshipType,
    SyncResult,
    SyncStatus,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AGE session initialization (run once per connection)
# ---------------------------------------------------------------------------

AGE_SESSION_INIT = text(
    "LOAD age; SET search_path TO ag_catalog, \"$current_schema\", public"
)

# ---------------------------------------------------------------------------
# Cypher query templates
# ---------------------------------------------------------------------------

_CREATE_VERTEX = text(
    """
    SELECT * FROM cypher('ontology_{graph_name}',
        $$ CREATE (n:OntoNode {
            id: $id,
            ontology_id: $ontology_id,
            type: $type,
            name: $name,
            name_zh: $name_zh,
            uri: $uri,
            definition: $definition,
            synonyms: $synonyms
        }) RETURN n $$,
        :params
    ) AS (vertex agtype);
    """
)

_CREATE_EDGE = text(
    """
    SELECT * FROM cypher('ontology_{graph_name}',
        $$ MATCH (a:OntoNode {{id: $from_id}}), (b:OntoNode {{id: $to_id}})
           CREATE (a)-[r:{rel_type} {{
               id: $rel_id,
               label: $label,
               weight: $weight
           }}]->(b)
           RETURN r $$,
        :params
    ) AS (edge agtype);
    """
)

_DROP_GRAPH = text(
    "SELECT drop_graph('ontology_{graph_name}', true);"
)

_CREATE_GRAPH = text(
    "SELECT create_graph('ontology_{graph_name}');"
)

_MARK_NODE_SYNCED = text(
    """
    UPDATE kg_nodes
       SET synced_to_graph = true,
           graph_synced_at   = :synced_at
     WHERE id = :node_id
    """
)

_MARK_EDGE_SYNCED = text(
    """
    UPDATE kg_edges
       SET synced_to_graph = true,
           graph_synced_at   = :synced_at
     WHERE id = :edge_id
    """
)

_COUNT_SYNCED_NODES = text(
    """
    SELECT
        COUNT(*) FILTER (WHERE synced_to_graph) AS synced,
        COUNT(*) FILTER (WHERE NOT synced_to_graph) AS unsynced,
        COUNT(*) AS total
      FROM kg_nodes
     WHERE corpus_id = :corpus_id
    """
)

_COUNT_SYNCED_EDGES = text(
    """
    SELECT
        COUNT(*) FILTER (WHERE synced_to_graph) AS synced,
        COUNT(*) FILTER (WHERE NOT synced_to_graph) AS unsynced,
        COUNT(*) AS total
      FROM kg_edges
     WHERE corpus_id = :corpus_id
    """
)

_FETCH_UNSYNCED_NODES = text(
    """
    SELECT id, corpus_id, ontology_id, node_type, name, name_zh,
           uri, definition, synonyms, properties
      FROM kg_nodes
     WHERE corpus_id = :corpus_id
       AND synced_to_graph = false
    """
)

_FETCH_ALL_NODES = text(
    """
    SELECT id, corpus_id, ontology_id, node_type, name, name_zh,
           uri, definition, synonyms, properties
      FROM kg_nodes
     WHERE corpus_id = :corpus_id
    """
)

_FETCH_UNSYNCED_EDGES = text(
    """
    SELECT id, corpus_id, source_node_id, target_node_id,
           relationship_type, label, properties, weight
      FROM kg_edges
     WHERE corpus_id = :corpus_id
       AND synced_to_graph = false
    """
)

_FETCH_ALL_EDGES = text(
    """
    SELECT id, corpus_id, source_node_id, target_node_id,
           relationship_type, label, properties, weight
      FROM kg_edges
     WHERE corpus_id = :corpus_id
    """
)

_GRAPH_EXISTS_QUERY = text(
    """
    SELECT EXISTS (
        SELECT 1 FROM ag_catalog.ag_graph
        WHERE name = :graph_name
    )
    """
)


# ---------------------------------------------------------------------------
# Row → frozen model helpers
# ---------------------------------------------------------------------------

def _row_to_kg_node(row: Any) -> KGNode:
    """Convert a database row to an immutable KGNode."""
    return KGNode(
        id=row.id,
        corpus_id=row.corpus_id,
        ontology_id=row.ontology_id,
        node_type=row.node_type,
        name=row.name,
        name_zh=row.name_zh,
        uri=row.uri,
        definition=row.definition,
        synonyms=list(row.synonyms) if row.synonyms else [],
        properties=dict(row.properties) if row.properties else {},
        synced_to_graph=row.synced_to_graph,
    )


def _row_to_kg_edge(row: Any) -> KGEdge:
    """Convert a database row to an immutable KGEdge."""
    return KGEdge(
        id=row.id,
        corpus_id=row.corpus_id,
        source_node_id=row.source_node_id,
        target_node_id=row.target_node_id,
        relationship_type=RelationshipType(row.relationship_type),
        label=row.label,
        properties=dict(row.properties) if row.properties else {},
        weight=row.weight,
        synced_to_graph=row.synced_to_graph,
    )


# ---------------------------------------------------------------------------
# Internal sync helpers
# ---------------------------------------------------------------------------

def _ensure_age_session(conn: Connection) -> None:
    """Ensure AGE extension is loaded and search path is set."""
    try:
        conn.execute(AGE_SESSION_INIT)
    except OperationalError as exc:
        raise RuntimeError(
            "Failed to initialize AGE session. "
            "Ensure the AGE extension is installed."
        ) from exc


def _graph_name(corpus_id: str) -> str:
    """Return the AGE graph name for a corpus."""
    return f"ontology_{corpus_id}"


def _sync_vertex(conn: Connection, node: KGNode, graph_name: str) -> None:
    """Create or merge an OntoNode vertex in the AGE graph."""
    params = {
        "id": str(node.id),
        "ontology_id": node.ontology_id,
        "type": node.node_type,
        "name": node.name,
        "name_zh": node.name_zh,
        "uri": node.uri,
        "definition": node.definition,
        "synonyms": node.synonyms,
    }
    stmt = text(_CREATE_VERTEX.text.format(graph_name=graph_name))
    conn.execute(stmt, {"params": params})

    now = datetime.now(UTC)
    conn.execute(
        _MARK_NODE_SYNCED,
        {"node_id": str(node.id), "synced_at": now},
    )


def _sync_edge(conn: Connection, edge: KGEdge, graph_name: str) -> None:
    """Create a typed relationship edge in the AGE graph."""
    rel_type = edge.relationship_type.value
    params = {
        "from_id": str(edge.source_node_id),
        "to_id": str(edge.target_node_id),
        "rel_id": str(edge.id),
        "label": edge.label,
        "weight": edge.weight,
    }
    stmt = text(_CREATE_EDGE.text.format(
        graph_name=graph_name,
        rel_type=rel_type,
    ))
    conn.execute(stmt, {"params": params})

    now = datetime.now(UTC)
    conn.execute(
        _MARK_EDGE_SYNCED,
        {"edge_id": str(edge.id), "synced_at": now},
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def sync_corpus_to_graph(
    conn: Connection,
    corpus_id: str,
    mode: str = "full",
) -> SyncResult:
    """Synchronize a corpus from relational tables to the AGE graph.

    Args:
        conn: Active SQLAlchemy connection with AGE loaded.
        corpus_id: UUID string identifying the corpus.
        mode: ``"full"`` drops and rebuilds the graph;
              ``"incremental"`` only syncs unsynced rows.

    Returns:
        Immutable SyncResult with counts and any errors.
    """
    _ensure_age_session(conn)
    gname = _graph_name(corpus_id)
    start = datetime.now(UTC)
    errors: list[str] = []
    nodes_synced = 0
    edges_synced = 0
    nodes_failed = 0
    edges_failed = 0

    try:
        if mode == "full":
            # Drop existing graph (ignore error if it doesn't exist)
            with suppress(DBAPIError):
                conn.execute(text(_DROP_GRAPH.text.format(graph_name=gname)))

            # Create fresh graph
            conn.execute(text(_CREATE_GRAPH.text.format(graph_name=gname)))

            # Fetch ALL nodes and edges
            node_rows = conn.execute(
                _FETCH_ALL_NODES, {"corpus_id": corpus_id}
            ).fetchall()
            edge_rows = conn.execute(
                _FETCH_ALL_EDGES, {"corpus_id": corpus_id}
            ).fetchall()
        elif mode == "incremental":
            # Graph must already exist for incremental sync
            exists = conn.execute(
                _GRAPH_EXISTS_QUERY, {"graph_name": gname}
            ).scalar()
            if not exists:
                raise RuntimeError(
                    f"Graph {gname} does not exist. "
                    f"Run full sync first."
                )

            node_rows = conn.execute(
                _FETCH_UNSYNCED_NODES, {"corpus_id": corpus_id}
            ).fetchall()
            edge_rows = conn.execute(
                _FETCH_UNSYNCED_EDGES, {"corpus_id": corpus_id}
            ).fetchall()
        else:
            raise ValueError(
                f"Invalid sync mode: {mode!r}. "
                f"Expected 'full' or 'incremental'."
            )

        # Handle empty corpus gracefully
        if not node_rows and not edge_rows:
            logger.info(
                "Corpus %s has no nodes or edges to sync (mode=%s)",
                corpus_id,
                mode,
            )
            return SyncResult(
                corpus_id=corpus_id,
                mode=mode,
                duration_seconds=(datetime.now(UTC) - start).total_seconds(),
            )

        # Sync vertices
        for row in node_rows:
            try:
                node = _row_to_kg_node(row)
                _sync_vertex(conn, node, gname)
                nodes_synced += 1
            except (DBAPIError, RuntimeError) as exc:
                nodes_failed += 1
                errors.append(
                    f"Node {getattr(row, 'id', '?')}: {exc}"
                )
                logger.warning("Failed to sync node %s: %s", row.id, exc)

        # Sync edges
        for row in edge_rows:
            try:
                edge = _row_to_kg_edge(row)
                _sync_edge(conn, edge, gname)
                edges_synced += 1
            except (DBAPIError, RuntimeError) as exc:
                edges_failed += 1
                errors.append(
                    f"Edge {getattr(row, 'id', '?')}: {exc}"
                )
                logger.warning("Failed to sync edge %s: %s", row.id, exc)

    except Exception as exc:
        errors.append(str(exc))
        logger.error("Sync failed for corpus %s: %s", corpus_id, exc)

    duration = (datetime.now(UTC) - start).total_seconds()
    result = SyncResult(
        corpus_id=corpus_id,
        mode=mode,
        nodes_synced=nodes_synced,
        edges_synced=edges_synced,
        nodes_failed=nodes_failed,
        edges_failed=edges_failed,
        errors=tuple(errors),
        duration_seconds=duration,
    )
    logger.info(
        "Sync complete for corpus %s: %d nodes, %d edges in %.2fs",
        corpus_id,
        nodes_synced,
        edges_synced,
        duration,
    )
    return result


def sync_node_to_graph(conn: Connection, node: KGNode) -> None:
    """Create or update a single AGE vertex from a KGNode.

    Args:
        conn: Active SQLAlchemy connection with AGE loaded.
        node: Immutable KGNode to sync.

    Raises:
        RuntimeError: If AGE session initialization fails.
        DBAPIError: If the Cypher query fails.
    """
    _ensure_age_session(conn)
    gname = _graph_name(str(node.corpus_id))
    _sync_vertex(conn, node, gname)


def sync_edge_to_graph(conn: Connection, edge: KGEdge) -> None:
    """Create or update a single AGE edge from a KGEdge.

    Args:
        conn: Active SQLAlchemy connection with AGE loaded.
        edge: Immutable KGEdge to sync.

    Raises:
        RuntimeError: If AGE session initialization fails.
        DBAPIError: If the Cypher query fails.
    """
    _ensure_age_session(conn)
    gname = _graph_name(str(edge.corpus_id))
    _sync_edge(conn, edge, gname)


def rebuild_ontology_graph(
    conn: Connection,
    corpus_id: str,
) -> SyncResult:
    """Full graph rebuild: drop → create_graph → load all vertices → load all edges.

    This is equivalent to ``sync_corpus_to_graph(corpus_id, mode="full")``.

    Args:
        conn: Active SQLAlchemy connection with AGE loaded.
        corpus_id: UUID string identifying the corpus.

    Returns:
        Immutable SyncResult with counts and any errors.
    """
    return sync_corpus_to_graph(conn, corpus_id, mode="full")


def get_sync_status(conn: Connection, corpus_id: str) -> SyncStatus:
    """Return sync statistics for a corpus.

    Counts synced vs. unsynced rows in kg_nodes and kg_edges, and checks
    whether the AGE graph exists.

    Args:
        conn: Active SQLAlchemy connection with AGE loaded.
        corpus_id: UUID string identifying the corpus.

    Returns:
        Immutable SyncStatus snapshot.
    """
    _ensure_age_session(conn)
    gname = _graph_name(corpus_id)

    graph_exists = conn.execute(
        _GRAPH_EXISTS_QUERY, {"graph_name": gname}
    ).scalar()

    node_row = conn.execute(
        _COUNT_SYNCED_NODES, {"corpus_id": corpus_id}
    ).fetchone()

    edge_row = conn.execute(
        _COUNT_SYNCED_EDGES, {"corpus_id": corpus_id}
    ).fetchone()

    return SyncStatus(
        corpus_id=corpus_id,
        total_nodes=node_row.total if node_row else 0,
        synced_nodes=node_row.synced if node_row else 0,
        unsynced_nodes=node_row.unsynced if node_row else 0,
        total_edges=edge_row.total if edge_row else 0,
        synced_edges=edge_row.synced if edge_row else 0,
        unsynced_edges=edge_row.unsynced if edge_row else 0,
        graph_exists=bool(graph_exists),
    )

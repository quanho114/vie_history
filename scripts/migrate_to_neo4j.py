#!/usr/bin/env python3
"""Script to migrate existing knowledge graph nodes and edges from PostgreSQL to Neo4j.

Usage:
    python scripts/migrate_to_neo4j.py [--clear]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

# Add backend directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

from app.core.database import get_db_context
from app.models.graph import KnowledgeEdge, KnowledgeNode
from app.services.graph.neo4j_service import Neo4jService


async def migrate(clear_existing: bool = False) -> None:
    """Load all nodes and edges from PostgreSQL and save them to Neo4j."""
    print("[INFO] Starting Neo4j Migration...")

    neo4j_svc = Neo4jService()
    connected = await neo4j_svc.check_connection()
    if not connected:
        print("[ERROR] Cannot connect to Neo4j database. Please check if Neo4j is running.")
        sys.exit(1)

    if clear_existing:
        print("[INFO] Clearing existing data in Neo4j...")
        await neo4j_svc.clear_database()

    print("[INFO] Fetching nodes and edges from PostgreSQL...")
    async with get_db_context() as db:
        # Fetch all nodes
        nodes_result = await db.execute(select(KnowledgeNode))
        nodes = list(nodes_result.scalars().all())

        # Fetch all edges
        edges_result = await db.execute(select(KnowledgeEdge))
        edges = list(edges_result.scalars().all())

    print(f"[INFO] Found {len(nodes)} nodes and {len(edges)} edges in PostgreSQL.")

    # Step 1: Migrate all nodes
    node_id_to_slug = {}
    success_nodes = 0
    for idx, node in enumerate(nodes, 1):
        print(f"[INFO] Migrating node [{idx}/{len(nodes)}]: {node.name} ({node.node_type})")
        try:
            # Generate or use slug
            slug = node.slug or node.name.lower().replace(" ", "-")
            node_id_to_slug[node.id] = slug

            await neo4j_svc.create_node(
                node_type=node.node_type,
                name=node.name,
                slug=slug,
                description=node.description,
                wiki_page_id=node.wiki_page_id,
                event_id=node.event_id,
                metadata_json=node.metadata_json or {},
            )
            success_nodes += 1
        except Exception as exc:
            print(f"[ERROR] Failed to migrate node {node.name}: {exc}")

    # Step 2: Migrate all edges
    success_edges = 0
    for idx, edge in enumerate(edges, 1):
        src_slug = node_id_to_slug.get(edge.source_id)
        tgt_slug = node_id_to_slug.get(edge.target_id)

        if not src_slug or not tgt_slug:
            print(f"[WARN] Skipping edge [{idx}/{len(edges)}]: missing source or target slug (source_id={edge.source_id}, target_id={edge.target_id})")
            continue

        print(f"[INFO] Migrating edge [{idx}/{len(edges)}]: {src_slug} --[{edge.edge_type}]--> {tgt_slug}")
        try:
            await neo4j_svc.create_edge(
                source_slug=src_slug,
                target_slug=tgt_slug,
                edge_type=edge.edge_type,
                description=edge.description,
                weight=edge.weight,
            )
            success_edges += 1
        except Exception as exc:
            print(f"[ERROR] Failed to migrate edge: {exc}")

    print(f"[SUCCESS] Migration completed! Migrated {success_nodes}/{len(nodes)} nodes, and {success_edges}/{len(edges)} edges.")
    await neo4j_svc.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate historical graph data to Neo4j")
    parser.add_argument("--clear", action="store_true", help="Clear Neo4j database before migrating")
    args = parser.parse_args()

    asyncio.run(migrate(clear_existing=args.clear))


if __name__ == "__main__":
    main()

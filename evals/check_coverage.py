#!/usr/bin/env python3
"""
Data Coverage and System Health Audit for HistoriAI.

Connects to all databases (Postgres, Qdrant, Elasticsearch, Neo4j, Redis)
and reports exact ingestion metrics, collection sizes, and health status.
"""

import sys
import os
import json
from pathlib import Path

# Add apps/api to PYTHONPATH to load config
ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT / "apps" / "api"))

try:
    from app.core.config import settings
except ImportError as exc:
    print(f"Error importing app configuration: {exc}")
    sys.exit(1)


def check_postgres() -> dict:
    """Check PostgreSQL database connection and count tables."""
    print("Checking PostgreSQL...")
    import psycopg2
    try:
        # Convert asyncpg URL to standard psycopg2 URL (swap driver name)
        db_url = settings.SYNC_DATABASE_URL
        conn = psycopg2.connect(db_url)
        with conn.cursor() as cur:
            # Count tables
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
            tables = [r[0] for r in cur.fetchall()]
            
            counts = {}
            for table in ["documents", "entities", "document_entities", "sessions", "users"]:
                if table in tables:
                    cur.execute(f"SELECT COUNT(*) FROM {table};")
                    counts[table] = cur.fetchone()[0]
                else:
                    counts[table] = "Table not found"
            
            conn.close()
            return {"status": "HEALTHY", "tables": tables, "counts": counts}
    except Exception as exc:
        return {"status": "UNHEALTHY", "error": str(exc)}


def check_qdrant() -> dict:
    """Check Qdrant Vector database and retrieve collection stats."""
    print("Checking Qdrant...")
    from qdrant_client import QdrantClient
    try:
        client = QdrantClient(url=settings.QDRANT_URL)
        collection_name = settings.QDRANT_COLLECTION
        
        # List all collections
        collections = client.get_collections()
        col_names = [c.name for c in collections.collections]
        
        if collection_name in col_names:
            col_info = client.get_collection(collection_name)
            points_count = col_info.points_count
            status = str(col_info.status)
            return {
                "status": "HEALTHY",
                "collection_found": True,
                "points_count": points_count,
                "collection_status": status,
                "all_collections": col_names
            }
        else:
            return {
                "status": "WARNING",
                "collection_found": False,
                "points_count": 0,
                "all_collections": col_names,
                "msg": f"Collection '{collection_name}' not found."
            }
    except Exception as exc:
        return {"status": "UNHEALTHY", "error": str(exc)}


def check_meilisearch() -> dict:
    """Check Meilisearch BM25 index and retrieve document stats."""
    print("Checking Meilisearch...")
    from meilisearch_python_sdk import Client
    try:
        client = Client(settings.MEILISEARCH_URL, settings.MEILISEARCH_MASTER_KEY)
        health = client.health()
        if health.status == "available":
            index_name = settings.MEILISEARCH_INDEX
            try:
                index = client.get_index(index_name)
                stats = index.get_stats()
                doc_count = stats.number_of_documents
                return {
                    "status": "HEALTHY",
                    "index_found": True,
                    "document_count": doc_count
                }
            except Exception as e:
                return {
                    "status": "WARNING",
                    "index_found": False,
                    "document_count": 0,
                    "msg": f"Index '{index_name}' not found: {e}"
                }
        else:
            return {"status": "UNHEALTHY", "error": f"Meilisearch status: {health.status}"}
    except Exception as exc:
        return {"status": "UNHEALTHY", "error": str(exc)}


def check_neo4j() -> dict:
    """Check Neo4j Bolt connection and count nodes & relationships."""
    print("Checking Neo4j...")
    from neo4j import GraphDatabase
    try:
        driver = GraphDatabase.driver(
            settings.NEO4J_URL,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        with driver.session() as session:
            # Count nodes
            nodes_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            # Count relationships
            rels_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            
        driver.close()
        return {
            "status": "HEALTHY",
            "nodes_count": nodes_count,
            "relationships_count": rels_count
        }
    except Exception as exc:
        return {"status": "UNHEALTHY", "error": str(exc)}


def check_redis() -> dict:
    """Check Redis cache status."""
    print("Checking Redis...")
    import redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        ping_ok = r.ping()
        keys_count = len(r.keys("*")) if ping_ok else 0
        return {
            "status": "HEALTHY" if ping_ok else "UNHEALTHY",
            "ping": ping_ok,
            "cached_keys_count": keys_count
        }
    except Exception as exc:
        return {"status": "UNHEALTHY", "error": str(exc)}


def main():
    print("=" * 60)
    print("HistoriAI Database & Ingestion Coverage Audit")
    print("=" * 60)
    print(f"PostgreSQL URL:  {settings.SYNC_DATABASE_URL}")
    print(f"Qdrant URL:      {settings.QDRANT_URL} (Collection: {settings.QDRANT_COLLECTION})")
    print(f"Meilisearch:     {settings.MEILISEARCH_URL} (Index: {settings.MEILISEARCH_INDEX})")
    print(f"Neo4j URL:       {settings.NEO4J_URL}")
    print(f"Redis URL:       {settings.REDIS_URL}")
    print("-" * 60)
    
    results = {
        "postgres": check_postgres(),
        "qdrant": check_qdrant(),
        "meilisearch": check_meilisearch(),
        "neo4j": check_neo4j(),
        "redis": check_redis()
    }
    
    print("\n" + "=" * 60)
    print("AUDIT RESULTS SUMMARY")
    print("=" * 60)
    
    overall_healthy = True
    for db, info in results.items():
        status = info.get("status", "UNKNOWN")
        if status == "UNHEALTHY":
            overall_healthy = False
            
        print(f"[{status:9s}] {db.upper()}")
        if "error" in info:
            print(f"  Error: {info['error']}")
        else:
            for k, v in info.items():
                if k != "status":
                    print(f"  - {k}: {v}")
    
    print("-" * 60)
    print(f"OVERALL SYSTEM STATUS: {'✅ HEALTHY' if overall_healthy else '❌ DEGRADED'}")
    print("=" * 60)
    
    # Save audit report
    report_path = ROOT / "evals" / "coverage_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Full report saved to {report_path}")
    
    sys.exit(0 if overall_healthy else 1)


if __name__ == "__main__":
    main()

"""Performance indexes for hot query paths.

This migration adds indexes to improve query performance for:
- Document listing and filtering
- Session queries by user
- Audit log queries
- Knowledge draft queries by status
"""

from alembic import op
import sqlalchemy as sa


revision = "perf_indexes_001"
down_revision = "a5c68d4723b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Document chunks: composite index for retrieval
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chunks_document_id_index
        ON document_chunks(document_id, chunk_index)
    """)

    # Sessions by user and recency
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_user_updated
        ON sessions(user_id, updated_at DESC)
        WHERE user_id IS NOT NULL
    """)

    # Audit logs: composite indexes for common query patterns
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_actor_timestamp
        ON audit_logs(actor_id, timestamp DESC)
        WHERE actor_id IS NOT NULL
    """)

    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_risk_timestamp
        ON audit_logs(risk_level, timestamp DESC)
        WHERE risk_level IN ('warning', 'critical')
    """)

    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_ip_timestamp
        ON audit_logs(ip_address, timestamp DESC)
        WHERE ip_address IS NOT NULL
    """)

    # Knowledge drafts: pending review queue
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_drafts_status_pending
        ON knowledge_drafts(created_at DESC)
        WHERE status = 'pending'
    """)

    # Documents: status filtering
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_status_created
        ON documents(status, created_at DESC)
    """)

    # Messages: session + time ordering
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_session_created
        ON messages(session_id, created_at)
    """)

    # Analyze tables to update query planner statistics
    op.execute("ANALYZE document_chunks")
    op.execute("ANALYZE sessions")
    op.execute("ANALYZE audit_logs")
    op.execute("ANALYZE knowledge_drafts")
    op.execute("ANALYZE documents")
    op.execute("ANALYZE messages")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_chunks_document_id_index")
    op.execute("DROP INDEX IF EXISTS idx_sessions_user_updated")
    op.execute("DROP INDEX IF EXISTS idx_audit_logs_actor_timestamp")
    op.execute("DROP INDEX IF EXISTS idx_audit_logs_risk_timestamp")
    op.execute("DROP INDEX IF EXISTS idx_audit_logs_ip_timestamp")
    op.execute("DROP INDEX IF EXISTS idx_knowledge_drafts_status_pending")
    op.execute("DROP INDEX IF EXISTS idx_documents_status_created")
    op.execute("DROP INDEX IF EXISTS idx_messages_session_created")

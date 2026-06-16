"""Add brain tables and document historical metadata columns.

Revision ID: 002_brain
Revises: 001_initial
Create Date: 2026-05-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_brain'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # Phase 1 – Add historical-metadata columns to existing documents table
    # ------------------------------------------------------------------ #
    op.add_column(
        'documents',
        sa.Column('period', sa.String(50), nullable=True),
    )
    op.add_column(
        'documents',
        sa.Column('year', sa.Integer, nullable=True),
    )
    op.add_column(
        'documents',
        sa.Column('event_type', sa.String(50), nullable=True),
    )
    op.add_column(
        'documents',
        sa.Column('confidence', sa.Float, nullable=False, server_default='0.0'),
    )
    op.add_column(
        'documents',
        sa.Column('historical_metadata', postgresql.JSONB, nullable=True),
    )

    # ------------------------------------------------------------------ #
    # Phase 2 – Wiki Brain tables
    # ------------------------------------------------------------------ #

    # wiki_pages
    op.create_table(
        'wiki_pages',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('slug', sa.String(500), unique=True, nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('content', postgresql.JSONB, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('event_type', sa.String(50), nullable=True),
        sa.Column('period', sa.String(50), nullable=True),
        sa.Column('start_year', sa.Integer, nullable=True),
        sa.Column('end_year', sa.Integer, nullable=True),
        sa.Column('source_document_ids', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column(
            'created_by',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index('idx_wiki_pages_slug', 'wiki_pages', ['slug'])
    op.create_index('idx_wiki_pages_status', 'wiki_pages', ['status'])
    op.create_index('idx_wiki_pages_period', 'wiki_pages', ['period'])
    op.create_index('idx_wiki_pages_event_type', 'wiki_pages', ['event_type'])

    # wiki_page_versions
    op.create_table(
        'wiki_page_versions',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            'wiki_page_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('wiki_pages.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('version', sa.Integer, nullable=False),
        sa.Column('content_snapshot', postgresql.JSONB, nullable=True),
        sa.Column('change_summary', sa.Text, nullable=True),
        sa.Column(
            'created_by',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint('wiki_page_id', 'version', name='uq_wiki_page_version'),
    )
    op.create_index('idx_wiki_page_versions_wiki_page_id', 'wiki_page_versions', ['wiki_page_id'])

    # wiki_links
    op.create_table(
        'wiki_links',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            'source_page_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('wiki_pages.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'target_page_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('wiki_pages.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('link_type', sa.String(50), nullable=False, server_default='related'),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index('idx_wiki_links_source', 'wiki_links', ['source_page_id'])
    op.create_index('idx_wiki_links_target', 'wiki_links', ['target_page_id'])

    # wiki_claims
    op.create_table(
        'wiki_claims',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            'wiki_page_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('wiki_pages.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('claim_text', sa.Text, nullable=False),
        sa.Column('section', sa.String(100), nullable=True),
        sa.Column('confidence', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('verified', sa.Boolean, nullable=False, server_default='false'),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index('idx_wiki_claims_wiki_page_id', 'wiki_claims', ['wiki_page_id'])
    op.create_index('idx_wiki_claims_verified', 'wiki_claims', ['verified'])

    # wiki_sources
    op.create_table(
        'wiki_sources',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            'wiki_claim_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('wiki_claims.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'document_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('documents.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column(
            'chunk_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('document_chunks.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('excerpt', sa.Text, nullable=True),
        sa.Column('relevance_score', sa.Float, nullable=False, server_default='0.0'),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index('idx_wiki_sources_claim_id', 'wiki_sources', ['wiki_claim_id'])
    op.create_index('idx_wiki_sources_document_id', 'wiki_sources', ['document_id'])

    # brain_build_jobs
    op.create_table(
        'brain_build_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('job_type', sa.String(50), nullable=False, server_default='wiki_build'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('source_document_ids', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('result_summary', postgresql.JSONB, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('logs', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column(
            'created_by',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index('idx_brain_build_jobs_status', 'brain_build_jobs', ['status'])
    op.create_index('idx_brain_build_jobs_created_at', 'brain_build_jobs', ['created_at'])

    # brain_review_plans
    op.create_table(
        'brain_review_plans',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            'job_id',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('brain_build_jobs.id', ondelete='CASCADE'),
            unique=True,
            nullable=False,
        ),
        sa.Column('proposed_pages', postgresql.JSONB, nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('admin_notes', sa.Text, nullable=True),
        sa.Column(
            'reviewed_by',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index('idx_brain_review_plans_status', 'brain_review_plans', ['status'])
    op.create_index('idx_brain_review_plans_job_id', 'brain_review_plans', ['job_id'])


def downgrade() -> None:
    # Drop brain tables in reverse dependency order
    op.drop_table('brain_review_plans')
    op.drop_table('brain_build_jobs')
    op.drop_table('wiki_sources')
    op.drop_table('wiki_claims')
    op.drop_table('wiki_links')
    op.drop_table('wiki_page_versions')
    op.drop_table('wiki_pages')

    # Remove Phase 1 columns
    op.drop_column('documents', 'historical_metadata')
    op.drop_column('documents', 'confidence')
    op.drop_column('documents', 'event_type')
    op.drop_column('documents', 'year')
    op.drop_column('documents', 'period')

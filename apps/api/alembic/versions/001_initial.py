"""Initial migration

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('username', sa.String(100), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), default='user', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_username', 'users', ['username'])

    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('source_url', sa.Text, nullable=True),
        sa.Column('canonical_url', sa.Text, unique=True, nullable=True),
        sa.Column('source_domain', sa.String(255), nullable=True),
        sa.Column('source_type', sa.String(50), default='unknown'),
        sa.Column('author', sa.String(255), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('language', sa.String(10), default='vi'),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('detected_years', postgresql.ARRAY(sa.Integer), nullable=True),
        sa.Column('entity_persons', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('entity_places', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('entity_organizations', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('entity_events', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('quality_score', sa.Float, default=0.0),
        sa.Column('raw_content_path', sa.Text, nullable=True),
        sa.Column('markdown_content_path', sa.Text, nullable=True),
        sa.Column('metadata_json', postgresql.JSONB, nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('idx_documents_status', 'documents', ['status'])
    op.create_index('idx_documents_created_at', 'documents', ['created_at'])
    op.create_index('ix_documents_canonical_url', 'documents', ['canonical_url'])

    # Create document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_index', sa.Integer, nullable=False),
        sa.Column('section_title', sa.String(500), nullable=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('token_count', sa.Integer, nullable=True),
        sa.Column('vector_id', sa.String(255), nullable=True),
        sa.Column('chunk_metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_chunks_document_id', 'document_chunks', ['document_id'])
    op.create_index('idx_chunks_token_count', 'document_chunks', ['token_count'])

    # Create ingest_jobs table
    op.create_table(
        'ingest_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('source_input', sa.Text, nullable=False),
        sa.Column('source_type', sa.String(20), default='url'),
        sa.Column('status', sa.String(20), default='queued'),
        sa.Column('stage', sa.String(50), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('logs', postgresql.JSONB, default=[]),
        sa.Column('document_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('mode', sa.String(50), nullable=True),
        sa.Column('citations', postgresql.JSONB, default=[]),
        sa.Column('trace', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_messages_session_id', 'messages', ['session_id'])

    # Create feedback table
    op.create_table(
        'feedback',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('message_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('score', sa.Integer, nullable=True),
        sa.Column('comment', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('score >= 1 AND score <= 5', name='check_feedback_score'),
    )

    # Create entities table
    op.create_table(
        'entities',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('normalized_name', sa.String(255), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('normalized_name', 'entity_type', name='uq_entities_normalized_type'),
    )
    op.create_index('idx_entities_normalized_name', 'entities', ['normalized_name'])
    op.create_index('idx_entities_type', 'entities', ['entity_type'])

    # Create document_entities table
    op.create_table(
        'document_entities',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('frequency', sa.Integer, default=1),
    )


def downgrade() -> None:
    op.drop_table('document_entities')
    op.drop_table('entities')
    op.drop_table('feedback')
    op.drop_table('messages')
    op.drop_table('sessions')
    op.drop_table('ingest_jobs')
    op.drop_table('document_chunks')
    op.drop_table('documents')
    op.drop_table('users')

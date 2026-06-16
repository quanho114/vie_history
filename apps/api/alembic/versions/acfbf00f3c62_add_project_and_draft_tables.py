"""add project and draft tables

Revision ID: acfbf00f3c62
Revises: 003_timeline_graph
Create Date: 2026-05-22 08:27:26.555743

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'acfbf00f3c62'
down_revision: Union[str, None] = '003_timeline_graph'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get database connection inspector to conditionally create tables
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create projects table if not exists
    if 'projects' not in tables:
        op.create_table(
            'projects',
            sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
            sa.Column('slug', sa.String(length=500), nullable=False),
            sa.Column('name', sa.String(length=500), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('created_by', sa.UUID(as_uuid=False), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('slug', name='uq_projects_slug')
        )
        op.create_index('idx_projects_created_at', 'projects', ['created_at'], unique=False)
        op.create_index('idx_projects_slug', 'projects', ['slug'], unique=False)

    # 2. Create project_members table if not exists
    if 'project_members' not in tables:
        op.create_table(
            'project_members',
            sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
            sa.Column('project_id', sa.UUID(as_uuid=False), nullable=False),
            sa.Column('user_id', sa.UUID(as_uuid=False), nullable=False),
            sa.Column('role', sa.String(length=50), nullable=False, server_default='viewer'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('project_id', 'user_id', name='uq_project_members_project_user')
        )
        op.create_index('idx_project_members_project', 'project_members', ['project_id'], unique=False)
        op.create_index('idx_project_members_user', 'project_members', ['user_id'], unique=False)

    # 3. Create project_sources table if not exists
    if 'project_sources' not in tables:
        op.create_table(
            'project_sources',
            sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
            sa.Column('project_id', sa.UUID(as_uuid=False), nullable=False),
            sa.Column('document_id', sa.UUID(as_uuid=False), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('project_id', 'document_id', name='uq_project_sources_project_doc')
        )
        op.create_index('idx_project_sources_doc', 'project_sources', ['document_id'], unique=False)
        op.create_index('idx_project_sources_project', 'project_sources', ['project_id'], unique=False)

    # 4. Modify existing tables
    op.alter_column('document_entities', 'frequency',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.add_column('documents', sa.Column('project_id', sa.UUID(as_uuid=False), nullable=True))
    op.alter_column('documents', 'source_type',
               existing_type=sa.VARCHAR(length=50),
               nullable=False)
    op.alter_column('documents', 'language',
               existing_type=sa.VARCHAR(length=10),
               nullable=False)
    op.alter_column('documents', 'status',
               existing_type=sa.VARCHAR(length=20),
               nullable=False)
    op.alter_column('documents', 'quality_score',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=False)
    op.alter_column('documents', 'confidence',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=False,
               existing_server_default=sa.text('0.0'))
    op.drop_constraint(op.f('documents_canonical_url_key'), 'documents', type_='unique')
    op.drop_index(op.f('ix_documents_canonical_url'), table_name='documents')
    op.create_index(op.f('ix_documents_canonical_url'), 'documents', ['canonical_url'], unique=True)
    op.create_unique_constraint('uq_documents_canonical_url', 'documents', ['canonical_url'])
    op.create_foreign_key(None, 'documents', 'projects', ['project_id'], ['id'], ondelete='SET NULL')
    op.alter_column('ingest_jobs', 'source_type',
               existing_type=sa.VARCHAR(length=20),
               nullable=False)
    op.alter_column('ingest_jobs', 'status',
               existing_type=sa.VARCHAR(length=20),
               nullable=False)
    op.alter_column('ingest_jobs', 'logs',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               nullable=False)
    op.drop_index(op.f('idx_messages_session_id'), table_name='messages')
    op.create_index(op.f('ix_messages_session_id'), 'messages', ['session_id'], unique=False)
    op.drop_constraint(op.f('users_email_key'), 'users', type_='unique')
    op.drop_constraint(op.f('users_username_key'), 'users', type_='unique')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.add_column('wiki_pages', sa.Column('project_id', sa.UUID(as_uuid=False), nullable=True))
    op.create_index('idx_wiki_pages_project_slug', 'wiki_pages', ['project_id', 'slug'], unique=False)
    op.create_foreign_key(None, 'wiki_pages', 'projects', ['project_id'], ['id'], ondelete='SET NULL')

    # 5. Create wiki_page_drafts table if not exists
    if 'wiki_page_drafts' not in tables:
        op.create_table(
            'wiki_page_drafts',
            sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
            sa.Column('wiki_page_id', sa.UUID(as_uuid=False), nullable=True),
            sa.Column('project_id', sa.UUID(as_uuid=False), nullable=True),
            sa.Column('slug', sa.String(length=500), nullable=False),
            sa.Column('title', sa.String(length=500), nullable=False),
            sa.Column('summary', sa.Text(), nullable=True),
            sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
            sa.Column('admin_notes', sa.Text(), nullable=True),
            sa.Column('proposed_by', sa.UUID(as_uuid=False), nullable=True),
            sa.Column('reviewed_by', sa.UUID(as_uuid=False), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['proposed_by'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['wiki_page_id'], ['wiki_pages.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_wiki_page_drafts_project', 'wiki_page_drafts', ['project_id'], unique=False)
        op.create_index('idx_wiki_page_drafts_status', 'wiki_page_drafts', ['status'], unique=False)


def downgrade() -> None:
    # Get database connection inspector
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Drop drafts table if exists
    if 'wiki_page_drafts' in tables:
        op.drop_table('wiki_page_drafts')

    # Modify existing tables
    op.drop_constraint(None, 'wiki_pages', type_='foreignkey')
    op.drop_index('idx_wiki_pages_project_slug', table_name='wiki_pages')
    op.drop_column('wiki_pages', 'project_id')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=False)
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_unique_constraint(op.f('users_username_key'), 'users', ['username'], postgresql_nulls_not_distinct=False)
    op.create_unique_constraint(op.f('users_email_key'), 'users', ['email'], postgresql_nulls_not_distinct=False)
    op.drop_index(op.f('ix_messages_session_id'), table_name='messages')
    op.create_index(op.f('idx_messages_session_id'), 'messages', ['session_id'], unique=False)
    op.alter_column('ingest_jobs', 'logs',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               nullable=True)
    op.alter_column('ingest_jobs', 'status',
               existing_type=sa.VARCHAR(length=20),
               nullable=True)
    op.alter_column('ingest_jobs', 'source_type',
               existing_type=sa.VARCHAR(length=20),
               nullable=True)
    op.drop_constraint(None, 'documents', type_='foreignkey')
    op.drop_constraint('uq_documents_canonical_url', 'documents', type_='unique')
    op.drop_index(op.f('ix_documents_canonical_url'), table_name='documents')
    op.create_index(op.f('ix_documents_canonical_url'), 'documents', ['canonical_url'], unique=False)
    op.create_unique_constraint(op.f('documents_canonical_url_key'), 'documents', ['canonical_url'], postgresql_nulls_not_distinct=False)
    op.alter_column('documents', 'confidence',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=True,
               existing_server_default=sa.text('0.0'))
    op.alter_column('documents', 'quality_score',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=True)
    op.alter_column('documents', 'status',
               existing_type=sa.VARCHAR(length=20),
               nullable=True)
    op.alter_column('documents', 'language',
               existing_type=sa.VARCHAR(length=10),
               nullable=True)
    op.alter_column('documents', 'source_type',
               existing_type=sa.VARCHAR(length=50),
               nullable=True)
    op.drop_column('documents', 'project_id')
    op.alter_column('document_entities', 'frequency',
               existing_type=sa.INTEGER(),
               nullable=True)

    # Drop project tables if they exist
    if 'project_sources' in tables:
        op.drop_table('project_sources')
    if 'project_members' in tables:
        op.drop_table('project_members')
    if 'projects' in tables:
        op.drop_table('projects')


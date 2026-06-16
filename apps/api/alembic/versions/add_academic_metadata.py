"""add academic metadata fields

Revision ID: add_acad_meta_001
Revises: perf_indexes_001
Create Date: 2026-06-16

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'add_acad_meta_001'
down_revision: Union[str, None] = 'perf_indexes_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('documents', sa.Column('dynasty', sa.String(length=100), nullable=True))
    op.add_column('documents', sa.Column('geographical_region', sa.String(length=100), nullable=True))

def downgrade() -> None:
    op.drop_column('documents', 'geographical_region')
    op.drop_column('documents', 'dynasty')

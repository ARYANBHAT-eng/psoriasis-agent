"""initial_schema

Revision ID: 829ad91aeefd
Revises:
Create Date: 2026-05-20 22:53:31.552868

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '829ad91aeefd'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'daily_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.String(), nullable=False),
        sa.Column('itch', sa.Float(), nullable=False),
        sa.Column('redness', sa.Float(), nullable=False),
        sa.Column('scaling', sa.Float(), nullable=False),
        sa.Column('joint_pain', sa.Float(), nullable=False),
        sa.Column('fatigue', sa.Float(), nullable=False),
        sa.Column('stress_level', sa.Float(), nullable=False),
        sa.Column('sleep_quality', sa.Float(), nullable=False),
        sa.Column('diet_quality', sa.Float(), nullable=False),
        sa.Column('missed_medication', sa.Integer(), nullable=False),
        sa.Column('topical_applied', sa.Integer(), nullable=False),
        sa.Column('psoriasis_flare', sa.Integer(), nullable=False),
        sa.Column('notes', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_daily_entries_date'), 'daily_entries', ['date'], unique=True)
    op.create_index(op.f('ix_daily_entries_id'), 'daily_entries', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_daily_entries_id'), table_name='daily_entries')
    op.drop_index(op.f('ix_daily_entries_date'), table_name='daily_entries')
    op.drop_table('daily_entries')

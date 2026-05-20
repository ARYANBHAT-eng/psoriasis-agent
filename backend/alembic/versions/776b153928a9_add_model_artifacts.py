"""add_model_artifacts

Revision ID: 776b153928a9
Revises: a7bfb241e40e
Create Date: 2026-05-21 00:28:30.736154

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '776b153928a9'
down_revision: Union[str, None] = 'a7bfb241e40e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'model_artifacts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trained_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('artifact_bytes', sa.LargeBinary(), nullable=False),
        sa.Column('metrics_json', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_model_artifacts_id', 'model_artifacts', ['id'], unique=False)
    op.create_index('ix_model_artifacts_trained_at', 'model_artifacts', ['trained_at'], unique=False)
    op.create_index('ix_model_artifacts_is_active', 'model_artifacts', ['is_active'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_model_artifacts_is_active', table_name='model_artifacts')
    op.drop_index('ix_model_artifacts_trained_at', table_name='model_artifacts')
    op.drop_index('ix_model_artifacts_id', table_name='model_artifacts')
    op.drop_table('model_artifacts')

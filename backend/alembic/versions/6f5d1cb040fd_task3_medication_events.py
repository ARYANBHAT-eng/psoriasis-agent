"""task3_medication_events

Revision ID: 6f5d1cb040fd
Revises: 1df35e70a8b0
Create Date: 2026-05-25 15:03:30.014592

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f5d1cb040fd'
down_revision: Union[str, None] = '1df35e70a8b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "medication_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.String, nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("medication_name", sa.String, nullable=False),
        sa.Column("event_type", sa.String, nullable=False),
        sa.Column("dose", sa.String, nullable=True),
        sa.Column("notes", sa.String, nullable=True),
    )
    op.create_index("ix_medication_events_user_id", "medication_events", ["user_id"])
    op.create_index("ix_medication_events_date", "medication_events", ["date"])


def downgrade() -> None:
    op.drop_index("ix_medication_events_date", table_name="medication_events")
    op.drop_index("ix_medication_events_user_id", table_name="medication_events")
    op.drop_table("medication_events")

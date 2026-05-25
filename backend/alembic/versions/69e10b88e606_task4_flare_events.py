"""task4_flare_events

Revision ID: 69e10b88e606
Revises: 6f5d1cb040fd
Create Date: 2026-05-25 15:23:20.152116

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69e10b88e606'
down_revision: Union[str, None] = '6f5d1cb040fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "flare_events",
        sa.Column("id",                sa.Integer, primary_key=True),
        sa.Column("user_id",           sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("start_date",        sa.String, nullable=False),
        sa.Column("end_date",          sa.String, nullable=True),
        sa.Column("condition_type",    sa.String, nullable=False),
        sa.Column("severity",          sa.Integer, nullable=True),
        sa.Column("confidence_source", sa.String, nullable=False),
        sa.Column("notes",             sa.String, nullable=True),
        sa.Column("created_at",        sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_flare_events_user_id",    "flare_events", ["user_id"])
    op.create_index("ix_flare_events_start_date", "flare_events", ["start_date"])

    # Backfill: one FlareEvent per legacy entry where legacy_flare_flag is truthy.
    # Single-day assumption; condition_type="psoriasis" (predates PsA tracking).
    # Downgrade deletes these rows before dropping the table.
    op.execute("""
        INSERT INTO flare_events (user_id, start_date, end_date, condition_type, confidence_source)
        SELECT user_id, date, date, 'psoriasis', 'legacy'
        FROM entries
        WHERE legacy_flare_flag IS NOT NULL AND legacy_flare_flag != 0
    """)


def downgrade() -> None:
    # Delete backfilled rows first so the reverse is clean and idempotent.
    op.execute("DELETE FROM flare_events WHERE confidence_source = 'legacy'")
    op.drop_index("ix_flare_events_start_date", table_name="flare_events")
    op.drop_index("ix_flare_events_user_id",    table_name="flare_events")
    op.drop_table("flare_events")

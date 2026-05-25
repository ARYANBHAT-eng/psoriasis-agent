"""task2_external_triggers

Revision ID: 1df35e70a8b0
Revises: 02f40192a44c
Create Date: 2026-05-25 14:44:42.070124

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1df35e70a8b0'
down_revision: Union[str, None] = '02f40192a44c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create weather_captures table
    op.create_table(
        "weather_captures",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.String, nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("temperature_c",    sa.Float, nullable=True),
        sa.Column("humidity_pct",     sa.Float, nullable=True),
        sa.Column("uv_index",         sa.Float, nullable=True),
        sa.Column("precipitation_mm", sa.Float, nullable=True),
        sa.Column("cloud_cover_pct",  sa.Float, nullable=True),
        sa.Column("pressure_hpa",     sa.Float, nullable=True),
        sa.Column("source", sa.String, nullable=False, server_default="open-meteo"),
    )
    op.create_unique_constraint("uq_weather_user_date", "weather_captures", ["user_id", "date"])
    op.create_index("ix_weather_captures_user_id", "weather_captures", ["user_id"])

    # 2. Add new trigger columns to entries
    op.add_column("entries", sa.Column("alcohol_units",       sa.Integer, nullable=True))
    op.add_column("entries", sa.Column("illness_active",      sa.Boolean, nullable=True))
    op.add_column("entries", sa.Column("illness_description", sa.String,  nullable=True))
    op.add_column("entries", sa.Column("cycle_day_of_period", sa.Integer, nullable=True))


def downgrade() -> None:
    op.drop_column("entries", "cycle_day_of_period")
    op.drop_column("entries", "illness_description")
    op.drop_column("entries", "illness_active")
    op.drop_column("entries", "alcohol_units")

    op.drop_index("ix_weather_captures_user_id", table_name="weather_captures")
    op.drop_constraint("uq_weather_user_date", "weather_captures", type_="unique")
    op.drop_table("weather_captures")

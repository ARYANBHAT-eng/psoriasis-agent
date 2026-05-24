"""task1_clinical_data_model

Revision ID: 02f40192a44c
Revises: 776b153928a9
Create Date: 2026-05-24 20:47:04.252038

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '02f40192a44c'
down_revision: Union[str, None] = '776b153928a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create user_profiles table
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("has_psoriasis", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("has_psa", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("tracks_cycle", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("location_city", sa.String, nullable=True),
        sa.Column("location_lat", sa.Float, nullable=True),
        sa.Column("location_lon", sa.Float, nullable=True),
        sa.Column("timezone", sa.String, nullable=False, server_default="UTC"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 2. Rename table daily_entries → entries
    op.rename_table("daily_entries", "entries")

    # 3. Drop the old unique index on date (was unique globally, now composite)
    op.drop_index("ix_daily_entries_date", table_name="entries")

    # 4. Create non-unique index on date (for query performance)
    op.create_index("ix_entries_date", "entries", ["date"], unique=False)

    # 5. Rename psoriasis_flare → legacy_flare_flag, drop NOT NULL
    op.alter_column("entries", "psoriasis_flare", new_column_name="legacy_flare_flag", nullable=True)

    # 6. Add new nullable clinical columns
    op.add_column("entries", sa.Column("morning_stiffness_minutes", sa.Integer, nullable=True))
    op.add_column("entries", sa.Column("affected_joints", sa.JSON, nullable=True))
    op.add_column("entries", sa.Column("functional_limitation", sa.Integer, nullable=True))
    op.add_column("entries", sa.Column("bsa_estimate", sa.Float, nullable=True))
    op.add_column("entries", sa.Column("plaque_locations", sa.JSON, nullable=True))

    # 7. Add user_id as nullable first (required before backfill)
    op.add_column("entries", sa.Column("user_id", sa.Integer, nullable=True))

    # 8. Backfill from single existing user (no-op if no entries exist)
    op.execute("UPDATE entries SET user_id = (SELECT id FROM users ORDER BY id LIMIT 1)")

    # 9. Make user_id NOT NULL
    op.alter_column("entries", "user_id", nullable=False)

    # 10. Add FK constraint
    op.create_foreign_key(
        "fk_entries_user_id", "entries", "users",
        ["user_id"], ["id"], ondelete="CASCADE"
    )

    # 11. Add index on user_id
    op.create_index("ix_entries_user_id", "entries", ["user_id"])

    # 12. Add composite unique constraint (user_id, date)
    op.create_unique_constraint("uq_entries_user_date", "entries", ["user_id", "date"])


def downgrade() -> None:
    # Reverse order of upgrade

    # 12. Drop composite unique constraint
    op.drop_constraint("uq_entries_user_date", "entries", type_="unique")

    # 11. Drop user_id index
    op.drop_index("ix_entries_user_id", table_name="entries")

    # 10. Drop FK constraint
    op.drop_constraint("fk_entries_user_id", "entries", type_="foreignkey")

    # 9+8+7. Drop user_id column
    op.drop_column("entries", "user_id")

    # 6. Drop new nullable clinical columns
    op.drop_column("entries", "plaque_locations")
    op.drop_column("entries", "bsa_estimate")
    op.drop_column("entries", "functional_limitation")
    op.drop_column("entries", "affected_joints")
    op.drop_column("entries", "morning_stiffness_minutes")

    # 5. Rename legacy_flare_flag → psoriasis_flare, restore NOT NULL
    op.alter_column("entries", "legacy_flare_flag", new_column_name="psoriasis_flare", nullable=False)

    # 4. Drop the non-unique index on date
    op.drop_index("ix_entries_date", table_name="entries")

    # 3. Restore the unique index on date
    op.create_index("ix_daily_entries_date", "entries", ["date"], unique=True)

    # 2. Rename entries → daily_entries
    op.rename_table("entries", "daily_entries")

    # 1. Drop user_profiles table
    op.drop_table("user_profiles")

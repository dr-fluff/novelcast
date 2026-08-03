"""add user_daily_activity, user_devices, and chapters.word_count

Revision ID: a1c9e73f2b6d
Revises: 9c14a2fef001
Create Date: 2026-08-03 00:00:00.000000

Adds the storage needed for the user stats feature: word_count on
chapters (for reading-speed calculation), user_daily_activity (per-day
read_seconds, backing both total read time and the activity heatmap),
and user_devices (per-device first/last-seen, backing the device count
stat).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1c9e73f2b6d"
down_revision: Union[str, Sequence[str], None] = "9c14a2fef001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chapters", sa.Column("word_count", sa.Integer(), nullable=True))

    op.create_table(
        "user_daily_activity",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("activity_date", sa.Date(), primary_key=True),
        sa.Column("read_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "user_devices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("device_id", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("last_seen_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("user_id", "device_id", name="uq_user_devices_user_device"),
    )


def downgrade() -> None:
    op.drop_table("user_devices")
    op.drop_table("user_daily_activity")
    op.drop_column("chapters", "word_count")
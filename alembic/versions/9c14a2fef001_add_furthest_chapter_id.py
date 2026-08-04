"""add furthest_chapter_id to reading_progress

Revision ID: 9c14a2fef001
Revises: 7f2a9c1d3e5b
Create Date: 2026-08-02 00:00:00.000000

reading_progress.last_chapter_id was previously doing two jobs at once:
tracking the furthest chapter ever reached (forward-only, used for
read/unread marking) AND acting as the "continue reading" resume point
(which should follow wherever you most recently read, even if that's
earlier than your furthest point). Those two needed to be separate
columns — this adds furthest_chapter_id for the forward-only role,
backfilled from the current last_chapter_id (which, until now, WAS the
forward-only value). last_chapter_id itself keeps its column but its
write path changes going forward to update unconditionally, becoming
the true "most recently read" pointer.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c14a2fef001"
down_revision: str | Sequence[str] | None = "7f2a9c1d3e5b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add furthest_chapter_id, backfilled from the existing last_chapter_id.

    SQLite doesn't support ALTER TABLE ADD COLUMN with a foreign key
    constraint directly — Alembic requires batch mode here, which
    recreates the table under the hood (copy-and-move) rather than
    trying an in-place ALTER. Batch mode also requires the foreign key
    constraint to have an explicit name (it can't be anonymous), so the
    column and the constraint are added as two separate steps.
    """
    with op.batch_alter_table("reading_progress") as batch_op:
        batch_op.add_column(sa.Column("furthest_chapter_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_reading_progress_furthest_chapter_id_chapters",
            "chapters",
            ["furthest_chapter_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.execute("UPDATE reading_progress SET furthest_chapter_id = last_chapter_id")


def downgrade() -> None:
    """Drop furthest_chapter_id. last_chapter_id is untouched either way."""
    with op.batch_alter_table("reading_progress") as batch_op:
        batch_op.drop_column("furthest_chapter_id")

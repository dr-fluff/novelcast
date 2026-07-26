"""add locked_fields to stories

Revision ID: 4b37554c602a
Revises: 0d8c317c6925
Create Date: 2026-07-26 12:06:19.084074

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b37554c602a'
down_revision: Union[str, Sequence[str], None] = '0d8c317c6925'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("stories", sa.Column("locked_fields", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("stories", "locked_fields")
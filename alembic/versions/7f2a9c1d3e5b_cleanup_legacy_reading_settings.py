"""cleanup legacy non-device-scoped chapter reading settings

Revision ID: 7f2a9c1d3e5b
Revises: 4b37554c602a
Create Date: 2026-07-31 00:00:00.000000

A prior bug meant SettingsRepository was constructed without its
user_settings_schema, so every "reading" category setting (chapter
theme, font size, margin, etc.) fell back to category="preference"
and was saved as a single global row per user instead of being scoped
per device via the "device:<uuid>." name prefix. This deletes those
stale global rows for every user, on every affected installation, so
the corrected code can start writing clean device-scoped rows going
forward. There is no meaningful downgrade for a data deletion, so
downgrade() is a no-op.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7f2a9c1d3e5b'
down_revision: Union[str, Sequence[str], None] = '4b37554c602a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LEGACY_READING_SETTING_NAMES = (
    "chapter_theme",
    "chapter_font_family",
    "chapter_font_size",
    "chapter_line_spacing",
    "chapter_font_weight",
    "chapter_paragraph_spacing",
    "chapter_content_padding",
)


def upgrade() -> None:
    """Delete legacy global (non-device-scoped) reading setting rows."""
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM user_settings WHERE name IN :names"
        ).bindparams(sa.bindparam("names", expanding=True)),
        {"names": list(_LEGACY_READING_SETTING_NAMES)},
    )


def downgrade() -> None:
    """No-op — deleted rows (stale, incorrectly-global settings) are not recoverable
    and shouldn't be recreated even if this migration is rolled back."""
    pass